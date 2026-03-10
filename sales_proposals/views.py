from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from .models import Proposal, ProposalItem
from .forms import ProposalForm, ProposalItemFormSet
from customers.models import Customer
from users.models import User
from sales_monitoring.models import SalesActivity, ActivityType
from sales_funnel.models import SalesFunnel
from django.db import transaction
from django.utils import timezone
from django.conf import settings
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io
from django.core.mail import EmailMessage
import os

from reportlab.lib.utils import ImageReader

@login_required
def proposal_list(request):
    if request.user.role == 'salesperson':
        proposals = Proposal.objects.filter(created_by=request.user)
    elif request.user.role == 'supervisor':
        # Get groups managed by this supervisor
        managed_groups = request.user.managed_groups.all()
        # Get all users in these groups (salespeople)
        member_ids = []
        for group in managed_groups:
             member_ids.extend(group.members.values_list('user_id', flat=True))
        
        # Include proposals created by the supervisor themselves + their group members
        member_ids.append(request.user.id)
        proposals = Proposal.objects.filter(created_by_id__in=member_ids)
    elif request.user.role == 'avp':
        # Get teams managed by this AVP
        managed_teams = request.user.managed_teams.all()
        member_ids = []
        for team in managed_teams:
            for group in team.groups.all():
                member_ids.extend(group.members.values_list('user_id', flat=True))
                # Include group supervisors
                if group.supervisor:
                    member_ids.append(group.supervisor.id)
        
        member_ids.append(request.user.id)
        proposals = Proposal.objects.filter(created_by_id__in=member_ids)
    elif request.user.role == 'asm':
        # ASMs see all groups in their assigned teams
        from teams.models import Group
        assigned_teams = request.user.asm_teams.all()
        
        member_ids = []
        for team in assigned_teams:
            for group in team.groups.all():
                member_ids.extend(group.members.values_list('user_id', flat=True))
                if group.supervisor:
                    member_ids.append(group.supervisor.id)
        
        member_ids.append(request.user.id)
        proposals = Proposal.objects.filter(created_by_id__in=member_ids)
    elif request.user.role == 'teamlead':
        # Team Leads see their led groups
        led_groups = request.user.led_groups.all()
        member_ids = []
        for group in led_groups:
            member_ids.extend(group.members.values_list('user_id', flat=True))
        
        member_ids.append(request.user.id)
        proposals = Proposal.objects.filter(created_by_id__in=member_ids)
    else:
        # Admins, VPs, GMs see all
        proposals = Proposal.objects.all()
    
    # Get list of salespeople for filter dropdown (from the visible proposals)
    salespeople_ids = proposals.values_list('created_by', flat=True).distinct()
    salespeople = User.objects.filter(id__in=salespeople_ids).order_by('first_name', 'last_name')
    
    # Filter by salesperson if requested
    salesperson_id = request.GET.get('salesperson')
    if salesperson_id:
        try:
            salesperson_id = int(salesperson_id)
            proposals = proposals.filter(created_by_id=salesperson_id)
        except ValueError:
            salesperson_id = None
            
    context = {
        'proposals': proposals,
        'salespeople': salespeople,
        'selected_salesperson': salesperson_id
    }
    
    return render(request, 'sales_proposals/proposal_list.html', context)

@login_required
def proposal_create(request):
    if request.method == 'POST':
        form = ProposalForm(request.POST, user=request.user)
        formset = ProposalItemFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                proposal = form.save(commit=False)
                proposal.created_by = request.user
                proposal.save()
                
                items = formset.save(commit=False)
                for item in items:
                    item.proposal = proposal
                    item.save()
                
                proposal.calculate_totals()
                
                # Auto-update Sales Funnel
                update_sales_funnel(proposal)
                
                messages.success(request, 'Proposal created successfully.')
                return redirect('proposal_detail', pk=proposal.pk)
    else:
        form = ProposalForm(user=request.user)
        formset = ProposalItemFormSet()
    
    return render(request, 'sales_proposals/proposal_form.html', {
        'form': form,
        'formset': formset,
        'title': 'Create Proposal'
    })

@login_required
def proposal_update(request, pk):
    proposal = get_object_or_404(Proposal, pk=pk)
    if request.method == 'POST':
        form = ProposalForm(request.POST, instance=proposal, user=request.user)
        formset = ProposalItemFormSet(request.POST, instance=proposal)
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                form.save()
                items = formset.save(commit=False)
                for item in items:
                    item.proposal = proposal
                    item.save()
                for obj in formset.deleted_objects:
                    obj.delete()
                
                proposal.calculate_totals()
                update_sales_funnel(proposal)
                
                messages.success(request, 'Proposal updated successfully.')
                return redirect('proposal_detail', pk=proposal.pk)
    else:
        form = ProposalForm(instance=proposal, user=request.user)
        formset = ProposalItemFormSet(instance=proposal)
    
    return render(request, 'sales_proposals/proposal_form.html', {
        'form': form,
        'formset': formset,
        'title': 'Edit Proposal'
    })

@login_required
def proposal_detail(request, pk):
    proposal = get_object_or_404(Proposal, pk=pk)
    return render(request, 'sales_proposals/proposal_detail.html', {'proposal': proposal})

@login_required
def proposal_delete(request, pk):
    proposal = get_object_or_404(Proposal, pk=pk)
    if request.method == 'POST':
        proposal.delete()
        messages.success(request, 'Proposal deleted successfully.')
        return redirect('proposal_list')
    return render(request, 'sales_proposals/proposal_confirm_delete.html', {'proposal': proposal})

def generate_pdf_buffer(proposal):
    buffer = io.BytesIO()
    
    # Calculate footer height first to adjust bottom margin
    footer_img_path = os.path.join(settings.BASE_DIR, 'core/static/core/images/PROPOSAL-FOOTER.png')
    footer_height = 0
    footer_width = 7.5 * inch
    
    if os.path.exists(footer_img_path):
        try:
            img_reader = ImageReader(footer_img_path)
            iw, ih = img_reader.getSize()
            aspect = ih / float(iw)
            footer_height = footer_width * aspect
        except:
            footer_height = 0.5 * inch # Fallback
            
    # Reduced margins to fit more content and match the dense layout of the screenshot
    # Adjust bottom margin to accommodate footer + padding
    bottom_margin = max(36, footer_height + 20)
    
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=bottom_margin)
    styles = getSampleStyleSheet()
    
    # Custom Colors
    MIC_RED = colors.HexColor('#B22222') # Firebrick red, approximating the screenshot
    MIC_YELLOW = colors.HexColor('#FFFF00') # Yellow for the note
    
    # Custom Styles
    try:
        pdfmetrics.registerFont(TTFont('Arial', '/System/Library/Fonts/Supplemental/Arial.ttf'))
        pdfmetrics.registerFont(TTFont('Arial-Bold', '/System/Library/Fonts/Supplemental/Arial Bold.ttf'))
        font_normal = 'Arial'
        font_bold = 'Arial-Bold'
    except:
        font_normal = 'Helvetica'
        font_bold = 'Helvetica-Bold'

    styles.add(ParagraphStyle(name='HeaderContact', parent=styles['Normal'], fontName=font_normal, textColor=colors.white, fontSize=8, leading=10, alignment=TA_RIGHT))
    styles.add(ParagraphStyle(name='ProposalTitle', parent=styles['Heading1'], fontName=font_bold, fontSize=14, spaceAfter=6))
    styles.add(ParagraphStyle(name='NormalSmall', parent=styles['Normal'], fontName=font_normal, fontSize=9, leading=11))
    styles.add(ParagraphStyle(name='TableText', parent=styles['Normal'], fontName=font_normal, fontSize=8, leading=10))
    styles.add(ParagraphStyle(name='TableHeader', parent=styles['Normal'], fontName=font_bold, fontSize=8, leading=10, textColor=colors.white, alignment=TA_CENTER))
    styles.add(ParagraphStyle(name='NoteHeader', parent=styles['Normal'], fontName=font_bold, fontSize=9, backColor=MIC_YELLOW))

    def draw_footer(canvas, doc):
        canvas.saveState()
        if os.path.exists(footer_img_path):
            try:
                # Draw centered horizontally, at the bottom
                # x = (letter[0] - width) / 2
                x_pos = (letter[0] - footer_width) / 2
                y_pos = 10 # Small margin from bottom edge
                canvas.drawImage(footer_img_path, x_pos, y_pos, width=footer_width, height=footer_height, mask='auto')
            except Exception as e:
                pass
        canvas.restoreState()

    elements = []
    
    # --- HEADER ---
    # Try to use the full width header image first
    header_img_path = os.path.join(settings.BASE_DIR, 'core/static/core/images/Proposal_Header.png')
    
    if os.path.exists(header_img_path):
        # Full width header image
        # Assuming letter width is 8.5 inches. With 0.5 inch margins on each side, usable width is 7.5 inches.
        # We'll adjust height proportionally.
        img_width = 7.5 * inch
        
        # Read image to get aspect ratio
        try:
            img_reader = ImageReader(header_img_path)
            iw, ih = img_reader.getSize()
            aspect = ih / float(iw)
            img_height = img_width * aspect
        except:
             img_height = 1.2 * inch # Fallback
        
        header_img = Image(header_img_path, width=img_width, height=img_height)
        header_img.hAlign = 'CENTER'
        elements.append(header_img)
        elements.append(Spacer(1, 20))
        
    else:
        # Fallback to old header construction
        logo_path = os.path.join(settings.BASE_DIR, 'core/static/core/images/mi-logo-blk.png')
        logo_img = None
        if os.path.exists(logo_path):
            logo_img = Image(logo_path, width=2.5*inch, height=0.75*inch)
            logo_img.hAlign = 'LEFT'
        
        contact_text = """
        Unit 53, 62 & 101, Legaspi Suites Bldg.<br/>
        178 Salcedo St. Legaspi Village, Makati City<br/>
        8-840-4323<br/>
        www.microimageph.com
        """
        contact_para = Paragraph(contact_text, styles['HeaderContact'])
        
        header_data = [[logo_img if logo_img else "MICRO IMAGE", contact_para]]
        header_table = Table(header_data, colWidths=[4.5*inch, 3*inch])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BACKGROUND', (1,0), (1,0), MIC_RED),
            ('LEFTPADDING', (1,0), (1,0), 10),
            ('RIGHTPADDING', (1,0), (1,0), 10),
            ('TOPPADDING', (1,0), (1,0), 10),
            ('BOTTOMPADDING', (1,0), (1,0), 10),
            ('ALIGN', (0,0), (0,0), 'LEFT'),
            ('ALIGN', (1,0), (1,0), 'RIGHT'),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 20))
    
    # --- REFERENCE INFO ---
    ref_no = proposal.reference_number if proposal.reference_number else proposal.proposal_number
    elements.append(Paragraph(f"Ref No: {ref_no}", styles['NormalSmall']))
    elements.append(Paragraph(f"{proposal.date.strftime('%B %d, %Y')}", styles['NormalSmall']))
    elements.append(Spacer(1, 12))
    
    # --- CUSTOMER INFO ---
    elements.append(Paragraph(f"Ms./Mr. {proposal.customer.contact_person_name}", styles['NormalSmall']))
    elements.append(Paragraph(f"<b>{proposal.customer.company_name}</b>", styles['NormalSmall']))
    if proposal.customer.phone_number:
        elements.append(Paragraph(proposal.customer.phone_number, styles['NormalSmall']))
    if proposal.customer.email:
        elements.append(Paragraph(f"<a href='mailto:{proposal.customer.email}'>{proposal.customer.email}</a>", styles['NormalSmall']))
    elements.append(Spacer(1, 12))
    
    # --- SALUTATION ---
    elements.append(Paragraph("Dear Sir/Madame,", styles['NormalSmall']))
    elements.append(Spacer(1, 6))
    
    # --- OPENING ---
    intro_text = proposal.introduction if proposal.introduction else \
        "Micro Image International Corporation, an experienced and reputable IT products & services provider, with partnership appointments from various industry-leading products, is pleased to submit its quotation for your IT requirements."
    elements.append(Paragraph(intro_text, styles['NormalSmall']))
    elements.append(Spacer(1, 12))
    
    # --- ITEMS TABLE ---
    table_data = [[
        Paragraph("PART NUMBER", styles['TableHeader']),
        Paragraph("PRODUCT DESCRIPTION", styles['TableHeader']),
        Paragraph("QTY", styles['TableHeader']),
        Paragraph("UNIT PRICE", styles['TableHeader']),
        Paragraph("TOTAL PRICE", styles['TableHeader']),
        Paragraph("AVAILABILITY", styles['TableHeader'])
    ]]
    
    currency_symbol = '₱' if proposal.currency == 'PHP' else '$'
    
    for item in proposal.items.all():
        table_data.append([
            Paragraph(item.part_number, styles['TableText']),
            Paragraph(item.description, styles['TableText']),
            Paragraph(str(int(item.quantity)) if item.quantity % 1 == 0 else str(item.quantity), styles['TableText']),
            Paragraph(f"{currency_symbol} {item.unit_price:,.2f}", styles['TableText']),
            Paragraph(f"{currency_symbol} {item.amount:,.2f}", styles['TableText']),
            Paragraph(item.availability, styles['TableText'])
        ])
    
    # Subtotal
    table_data.append([
        '', '', '', 
        Paragraph("Subtotal", styles['TableText']), 
        Paragraph(f"{currency_symbol} {proposal.subtotal:,.2f}", styles['TableText']), 
        ''
    ])

    # Tax
    tax_label = None
    tax_amount_str = None

    if proposal.tax_type == 'VAT':
        tax_label = f"VAT ({proposal.tax_rate:.0f}%)"
        tax_amount_str = f"{currency_symbol} {proposal.tax_amount:,.2f}"
    elif proposal.tax_type == 'ZERO':
        tax_label = "Zero-Rated (0%)"
        tax_amount_str = f"{currency_symbol} 0.00"
    elif proposal.tax_type == 'EXEMPT':
        tax_label = "VAT-Exempt (0%)"
        tax_amount_str = f"{currency_symbol} 0.00"
    elif proposal.tax_rate > 0:
        tax_label = f"Tax ({proposal.tax_rate:.0f}%)"
        tax_amount_str = f"{currency_symbol} {proposal.tax_amount:,.2f}"

    if tax_label:
        table_data.append([
            '', '', '', 
            Paragraph(tax_label, styles['TableText']), 
            Paragraph(tax_amount_str, styles['TableText']), 
            ''
        ])

    # Total Investment Row
    table_data.append([
        '', '', '', 
        Paragraph("Total Investment", styles['TableHeader']), 
        Paragraph(f"{currency_symbol} {proposal.total_amount:,.2f}", styles['TableHeader']), 
        ''
    ])
    
    col_widths = [1.2*inch, 2.5*inch, 0.5*inch, 1.0*inch, 1.3*inch, 1.0*inch]
    t = Table(table_data, colWidths=col_widths, repeatRows=1)
    
    # Styling
    table_style = [
        ('BACKGROUND', (0,0), (-1,0), MIC_RED), # Header Background
        ('TEXTCOLOR', (0,0), (-1,0), colors.white), # Header Text
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-2), 1, colors.black), # Grid for all except last row
        ('ALIGN', (1,1), (1,-2), 'LEFT'), # Description Left
        
        # Total Row Styling
        ('BACKGROUND', (3,-1), (4,-1), MIC_RED),
        ('TEXTCOLOR', (3,-1), (4,-1), colors.white),
        ('GRID', (3,-1), (4,-1), 1, MIC_RED),
    ]
    t.setStyle(TableStyle(table_style))
    elements.append(t)
    elements.append(Spacer(1, 12))
    
    # --- NOTE ---
    if proposal.special_note:
        elements.append(Paragraph("Special Note:", styles['NormalSmall']))
        elements.append(Paragraph(proposal.special_note, styles['NoteHeader']))
        elements.append(Spacer(1, 12))
    
    # --- TERMS AND CONDITIONS ---
    tc_style = ParagraphStyle(name='TCText', parent=styles['NormalSmall'])
    tc_label = ParagraphStyle(name='TCLabel', parent=styles['NormalSmall'], fontName=font_bold)
    
    # Cancellation Text Logic
    cancellation_texts = {
        'professional': "To ensure we can commit the necessary resources to your project, please note that all confirmed Purchase Orders (POs) are considered final. As a result, any cancellation after confirmation will incur a fee equal to 100% of the total PO value.",
        'process': "As part of our commitment to efficiency, we begin resource allocation immediately upon PO confirmation. Therefore, any cancellation at this stage will result in a charge for the full order amount.",
        'polite': "Please be advised that once a Purchase Order is confirmed, it is firm and cannot be cancelled without liability. Should a cancellation occur, the client agrees to a fee amounting to 100% of the PO value.",
        'partnership': "In order to best serve our clients and allocate our production capacity effectively, we treat all confirmed Purchase Orders as binding commitments. We trust you understand that any cancellation would require a charge covering the full value of the order."
    }
    
    cancellation_text = cancellation_texts.get(proposal.cancellation_terms, cancellation_texts['professional'])
    
    tc_data = [
        [Paragraph("Terms and Conditions:", tc_label), ''],
        [Paragraph("Price", tc_label), Paragraph(f"Valid until {proposal.valid_until.strftime('%B %d, %Y') if proposal.valid_until else 'N/A'} only.", tc_style)],
        [Paragraph("Payment", tc_label), Paragraph(proposal.payment_terms, tc_style)],
        [Paragraph("Cancellation", tc_label), Paragraph(cancellation_text, tc_style)],
    ]

    if proposal.include_bank_details:
        tc_data.append([Paragraph("Bank Details", tc_label), Paragraph("MICRO IMAGE INTERNATIONAL CORP.<br/>Banco De Oro - Salcedo Dela Rosa Branch<br/>Golden Rock Bldg. Salcedo St. Legaspi Village Makati City 1200 Phils.", tc_style)])

    tc_data.extend([
        [Paragraph("Delivery Lead time", tc_label), Paragraph(proposal.delivery_lead_time, tc_style)],
        [Paragraph("Warranty", tc_label), Paragraph(proposal.warranty, tc_style)],
    ])
    
    if proposal.closing:
         tc_data.append([Paragraph("Other Terms", tc_label), Paragraph(proposal.closing.replace('\n', '<br/>'), tc_style)])

    tc_table = Table(tc_data, colWidths=[1.5*inch, 6*inch])
    tc_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (0,0), (0,-1), 'LEFT'),
    ]))
    elements.append(tc_table)
    elements.append(Spacer(1, 12))
    
    # --- CLOSING & SIGNATURES ---
    # We group Closing text + Signatures into a KeepTogether block to ensure they stay on the same page
    # If they don't fit, they will move to the next page together.
    
    closing_elements = []
    
    closing_elements.append(Paragraph("We trust that you keep this proposal with confidentiality and we hope that you find everything in order.", styles['NormalSmall']))
    closing_elements.append(Paragraph("Please fax Purchase Order/approval/conforme at (632) 894-25-90.", styles['NormalSmall']))
    closing_elements.append(Paragraph("Should you have any additional concern, please feel free to contact us.", styles['NormalSmall']))
    closing_elements.append(Spacer(1, 30))
    closing_elements.append(Paragraph("Very truly yours,", styles['NormalSmall']))
    closing_elements.append(Spacer(1, 30))
    
    sig_data = [
        ['', 'Conforme:'],
        ['', ''],
        ['__________________________', '__________________________'],
        [Paragraph(f"<b>{proposal.created_by.get_full_name()}</b><br/>Account Manager<br/>Mobile #: {proposal.created_by.mobile_number or ''}", styles['NormalSmall']), 
         Paragraph("Print Name & Sign<br/>Served as Order if signed by Authorized <br/>Representative", styles['NormalSmall'])]
    ]
    sig_table = Table(sig_data, colWidths=[3.5*inch, 4*inch])
    sig_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('BOTTOMPADDING', (0,1), (-1,1), 30), # Space for signature
    ]))
    closing_elements.append(sig_table)
    
    elements.append(KeepTogether(closing_elements))
    
    # --- FOOTER ---
    # Implemented via onFirstPage/onLaterPages callbacks
    
    doc.build(elements, onFirstPage=draw_footer, onLaterPages=draw_footer)
    buffer.seek(0)
    return buffer

@login_required
def proposal_pdf(request, pk):
    proposal = get_object_or_404(Proposal, pk=pk)
    buffer = generate_pdf_buffer(proposal)
    return HttpResponse(buffer, content_type='application/pdf')

@login_required
def proposal_email(request, pk):
    proposal = get_object_or_404(Proposal, pk=pk)
    
    # Determine supervisor email
    supervisor_email = None
    try:
        if hasattr(request.user, 'team_membership'):
            group = request.user.team_membership.group
            manager = group.get_manager()
            if manager and manager.email:
                supervisor_email = manager.email
    except Exception:
        pass
    
    if request.method == 'POST':
        # Get recipient email (allow override)
        recipient_email = request.POST.get('customer_email', proposal.customer.email)
        
        # Check for CC Supervisor
        cc_list = []
        if request.POST.get('cc_supervisor') == 'on' and supervisor_email:
            cc_list.append(supervisor_email)
            
        # Generate PDF
        buffer = generate_pdf_buffer(proposal)
        
        # Send Email
        subject = f"Proposal: {proposal.subject} - {proposal.proposal_number}"
        message = f"""Dear {proposal.customer.contact_person_name},

Please find attached our proposal for {proposal.subject}.

Best regards,
{proposal.created_by.get_full_name()}
"""
        email = EmailMessage(
            subject,
            message,
            request.user.email,
            [recipient_email],
            cc=cc_list,
            reply_to=[request.user.email]
        )
        email.attach(f"{proposal.proposal_number}.pdf", buffer.getvalue(), 'application/pdf')
        
        try:
            email.send()
            proposal.status = 'sent'
            proposal.save()
            
            # Log Activity
            log_sales_activity(proposal, request.user)
            
            # Update Funnel
            update_sales_funnel(proposal)
            
            msg = f"Proposal sent to {recipient_email}"
            if cc_list:
                msg += f" (CC: {', '.join(cc_list)})"
            messages.success(request, msg)
        except Exception as e:
            messages.error(request, f"Failed to send email: {str(e)}")
            
        return redirect('proposal_detail', pk=pk)
    
    return render(request, 'sales_proposals/proposal_email_confirm.html', {
        'proposal': proposal, 
        'supervisor_email': supervisor_email
    })

def log_sales_activity(proposal, user):
    # Find or create 'Proposal' activity type
    activity_type, _ = ActivityType.objects.get_or_create(
        name='Proposals',
        defaults={'icon': 'fas fa-file-alt', 'color': 'info'}
    )
    
    SalesActivity.objects.create(
        title=f"Sent Proposal: {proposal.proposal_number}",
        description=f"Sent proposal regarding {proposal.subject} to {proposal.customer.email}",
        activity_type=activity_type,
        salesperson=user,
        customer=proposal.customer,
        status='completed',
        priority='high',
        scheduled_start=timezone.now(),
        scheduled_end=timezone.now(),
        actual_start=timezone.now()
    )

def update_sales_funnel(proposal):
    # Determine PHP amounts for Sales Funnel (which tracks in PHP)
    if proposal.currency == 'USD':
        rate = proposal.exchange_rate if proposal.exchange_rate > 0 else 1.0
        retail_php = proposal.total_amount * rate
        cost_php = proposal.total_cost * rate
    else:
        retail_php = proposal.total_amount
        cost_php = proposal.total_cost

    # Try to find a funnel entry linked to this proposal
    funnel = SalesFunnel.objects.filter(proposal=proposal).first()
    
    if funnel:
        # Update existing linked funnel entry
        funnel.retail = retail_php
        funnel.cost = cost_php
        funnel.requirement_description = proposal.subject
        funnel.save()
    else:
        # Create new funnel entry linked to this proposal
        SalesFunnel.objects.create(
            date_created=proposal.date,
            company_name=proposal.customer.company_name,
            requirement_description=proposal.subject,
            cost=cost_php,
            retail=retail_php,
            stage='quoted', # Pink Funnel
            salesperson=proposal.created_by,
            customer=proposal.customer,
            deal_outcome='active',
            proposal=proposal
        )
