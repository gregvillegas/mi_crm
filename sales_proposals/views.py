from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from .models import Proposal, ProposalItem, ProposalApprovalStep, ProposalApprovalTier, ProposalChangeLog
from .forms import ProposalForm, ProposalItemFormSet, ProposalApprovalTierForm, ProposalApprovalTierImportForm, ProposalAttachmentFormSet
import csv
from decimal import Decimal
from django.http import FileResponse
from django.conf import settings
import os
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
            
    # Filter by Month if requested
    selected_month = request.GET.get('month')
    if selected_month:
        try:
            # selected_month format: YYYY-MM
            year, month = map(int, selected_month.split('-'))
            proposals = proposals.filter(date__year=year, date__month=month)
        except ValueError:
            selected_month = None

    # Calculate Total Value of filtered proposals (in PHP)
    total_proposals_value = 0
    for proposal in proposals:
        amount_php = proposal.total_amount
        if proposal.currency == 'USD':
            rate = proposal.exchange_rate if proposal.exchange_rate > 0 else 1.0
            amount_php = proposal.total_amount * rate
        total_proposals_value += amount_php

    # Group by Team for Executive Roles
    grouped_proposals = []
    show_team_grouping = False
    
    if request.user.role in ['admin', 'president', 'asm', 'vp', 'avp', 'gm']:
        show_team_grouping = True
        
        # Optimize query by prefetching related team info
        proposals = proposals.select_related('created_by__team_membership__group__team')
        
        teams_dict = {}
        
        for proposal in proposals:
            team_name = "Unassigned"
            try:
                if hasattr(proposal.created_by, 'team_membership'):
                    group = proposal.created_by.team_membership.group
                    if group and group.team:
                        team_name = group.team.name
            except Exception:
                pass
            
            if team_name not in teams_dict:
                teams_dict[team_name] = {
                    'name': team_name,
                    'proposals': [],
                    'total_investment': 0
                }
            
            teams_dict[team_name]['proposals'].append(proposal)
            
            # Calculate PHP equivalent for total
            amount_php = proposal.total_amount
            if proposal.currency == 'USD':
                rate = proposal.exchange_rate if proposal.exchange_rate > 0 else 1.0
                amount_php = proposal.total_amount * rate
            
            teams_dict[team_name]['total_investment'] += amount_php
            
        # Convert to list and sort
        grouped_proposals = list(teams_dict.values())
        # Sort by number of proposals (descending), then by team name
        grouped_proposals.sort(key=lambda x: (-len(x['proposals']), x['name']))

    # Get unique months for filter dropdown
    proposal_months = Proposal.objects.dates('date', 'month', order='DESC')
    
    context = {
        'proposals': proposals,
        'salespeople': salespeople,
        'selected_salesperson': salesperson_id,
        'proposal_months': proposal_months,
        'selected_month': selected_month,
        'total_proposals_value': total_proposals_value,
        'show_team_grouping': show_team_grouping,
        'grouped_proposals': grouped_proposals
    }
    
    return render(request, 'sales_proposals/proposal_list.html', context)

@login_required
def proposal_create(request):
    customer_id = request.GET.get('customer')
    customer = None
    if customer_id:
        customer = get_object_or_404(Customer, pk=customer_id)

    if request.method == 'POST':
        form = ProposalForm(request.POST, user=request.user)
        formset = ProposalItemFormSet(request.POST)
        attach_formset = ProposalAttachmentFormSet(request.POST, request.FILES)
        if form.is_valid() and formset.is_valid() and attach_formset.is_valid():
            with transaction.atomic():
                proposal = form.save(commit=False)
                proposal.created_by = request.user
                proposal.save()
                
                items = formset.save(commit=False)
                for item in items:
                    item.proposal = proposal
                    item.save()
                # Save attachments
                attachments = attach_formset.save(commit=False)
                for att in attachments:
                    att.proposal = proposal
                    att.uploaded_by = request.user
                    att.save()
                
                proposal.calculate_totals()
                proposal.ensure_approval_chain()
                
                # Auto-update Sales Funnel
                update_sales_funnel(proposal)
                
                messages.success(request, 'Proposal created successfully.')
                return redirect('proposal_detail', pk=proposal.pk)
    else:
        initial_data = {}
        if customer:
            initial_data['customer'] = customer
            
        form = ProposalForm(initial=initial_data, user=request.user)
        formset = ProposalItemFormSet()
        attach_formset = ProposalAttachmentFormSet()
    
    return render(request, 'sales_proposals/proposal_form.html', {
        'form': form,
        'formset': formset,
        'attach_formset': attach_formset,
        'title': 'Create Proposal',
        'customer': customer
    })

@login_required
def proposal_update(request, pk):
    proposal = get_object_or_404(Proposal, pk=pk)
    if request.method == 'POST':
        form = ProposalForm(request.POST, instance=proposal, user=request.user)
        formset = ProposalItemFormSet(request.POST, instance=proposal)
        attach_formset = ProposalAttachmentFormSet(request.POST, request.FILES, instance=proposal)
        if form.is_valid() and formset.is_valid() and attach_formset.is_valid():
            with transaction.atomic():
                before = Proposal.objects.get(pk=proposal.pk)
                before_items = {i.pk: {'part_number': i.part_number, 'description': i.description, 'quantity': str(i.quantity), 'unit_cost': str(i.unit_cost), 'unit_price': str(i.unit_price), 'warranty': i.warranty} for i in before.items.all()}
                updated = form.save()
                items = formset.save(commit=False)
                for item in items:
                    item.proposal = proposal
                    item.save()
                for obj in formset.deleted_objects:
                    obj.delete()
                # Save attachments
                attachments = attach_formset.save(commit=False)
                for att in attachments:
                    att.proposal = proposal
                    att.uploaded_by = request.user
                    att.save()
                for obj in attach_formset.deleted_objects:
                    obj.delete()
                
                proposal.calculate_totals()
                proposal.ensure_approval_chain()
                update_sales_funnel(proposal)
                # Change log
                changes = {}
                from django.forms.models import model_to_dict
                after = Proposal.objects.get(pk=proposal.pk)
                fields_to_check = ['customer_id','date','valid_until','subject','payment_terms','delivery_lead_time','warranty','special_note','introduction','closing','tax_type','tax_rate','include_bank_details','currency','exchange_rate']
                for f in fields_to_check:
                    if getattr(before, f) != getattr(after, f):
                        changes[f] = {'from': str(getattr(before, f)), 'to': str(getattr(after, f))}
                # Items
                after_items = {i.pk: {'part_number': i.part_number, 'description': i.description, 'quantity': str(i.quantity), 'unit_cost': str(i.unit_cost), 'unit_price': str(i.unit_price), 'warranty': i.warranty} for i in proposal.items.all()}
                item_changes = {}
                for pk_i, before_data in before_items.items():
                    if pk_i not in after_items:
                        item_changes[str(pk_i)] = {'status': 'deleted', 'before': before_data}
                    elif after_items[pk_i] != before_data:
                        item_changes[str(pk_i)] = {'status': 'updated', 'before': before_data, 'after': after_items[pk_i]}
                for pk_i, after_data in after_items.items():
                    if pk_i not in before_items:
                        item_changes[str(pk_i)] = {'status': 'added', 'after': after_data}
                if item_changes:
                    changes['items'] = item_changes
                if changes:
                    ProposalChangeLog.objects.create(proposal=proposal, changed_by=request.user, summary='Proposal updated', details=changes)
                
                messages.success(request, 'Proposal updated successfully.')
                return redirect('proposal_detail', pk=proposal.pk)
    else:
        form = ProposalForm(instance=proposal, user=request.user)
        formset = ProposalItemFormSet(instance=proposal)
        attach_formset = ProposalAttachmentFormSet(instance=proposal)
    
    return render(request, 'sales_proposals/proposal_form.html', {
        'form': form,
        'formset': formset,
        'attach_formset': attach_formset,
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
        # Define potential font paths for different OS
        # Note: prioritized order. Liberation Sans is preferred on Linux as it supports the Peso sign (₱).
        # We check for Liberation Sans *before* Arial to avoid loading old Arial versions that lack the symbol.
        arial_paths = [
            os.path.join(settings.BASE_DIR, 'core/static/core/fonts/LiberationSans-Regular.ttf'),
            '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf', # Ubuntu/Debian (System)
            os.path.join(settings.BASE_DIR, 'core/static/core/fonts/Arial.ttf'),
            '/System/Library/Fonts/Supplemental/Arial.ttf', # macOS
            '/usr/share/fonts/truetype/msttcorefonts/Arial.ttf', # Ubuntu/Debian (Often old version without Peso sign)
            '/usr/share/fonts/truetype/msttcorefonts/arial.ttf', # Ubuntu/Debian (lowercase)
            '/usr/share/fonts/TTF/Arial.ttf', # Arch/Manjaro
        ]
        
        arial_bold_paths = [
            os.path.join(settings.BASE_DIR, 'core/static/core/fonts/LiberationSans-Bold.ttf'),
            '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf', # Ubuntu/Debian (System)
            os.path.join(settings.BASE_DIR, 'core/static/core/fonts/Arial_Bold.ttf'),
            '/System/Library/Fonts/Supplemental/Arial Bold.ttf', # macOS
            '/usr/share/fonts/truetype/msttcorefonts/Arial_Bold.ttf', # Ubuntu/Debian
            '/usr/share/fonts/truetype/msttcorefonts/arialbd.ttf', # Ubuntu/Debian (lowercase)
            '/usr/share/fonts/TTF/Arialbd.ttf', # Arch/Manjaro
        ]
        
        # Find first existing Arial font
        arial_font = None
        for path in arial_paths:
            if os.path.exists(path):
                arial_font = path
                break
                
        # Find first existing Arial Bold font
        arial_bold_font = None
        for path in arial_bold_paths:
            if os.path.exists(path):
                arial_bold_font = path
                break
        
        if arial_font and arial_bold_font:
            pdfmetrics.registerFont(TTFont('Arial', arial_font))
            pdfmetrics.registerFont(TTFont('Arial-Bold', arial_bold_font))
            font_normal = 'Arial'
            font_bold = 'Arial-Bold'
        else:
            raise Exception("Arial font not found")
            
    except:
        # Fallback if Arial is not found anywhere
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
    contact_name = proposal.contact_name or proposal.customer.contact_person_name
    contact_email = proposal.contact_email or proposal.customer.email
    contact_phone = proposal.contact_phone or proposal.customer.phone_number
    elements.append(Paragraph(f"Ms./Mr. {contact_name}", styles['NormalSmall']))
    elements.append(Paragraph(f"<b>{proposal.customer.company_name}</b>", styles['NormalSmall']))
    if contact_phone:
        elements.append(Paragraph(contact_phone, styles['NormalSmall']))
    if contact_email:
        elements.append(Paragraph(f"<a href='mailto:{contact_email}'>{contact_email}</a>", styles['NormalSmall']))
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
        Paragraph("ITEM #", styles['TableHeader']),
        Paragraph("PART NUMBER", styles['TableHeader']),
        Paragraph("PRODUCT DESCRIPTION", styles['TableHeader']),
        Paragraph("QTY", styles['TableHeader']),
        Paragraph("UNIT PRICE", styles['TableHeader']),
        Paragraph("TOTAL PRICE", styles['TableHeader']),
        Paragraph("WARRANTY", styles['TableHeader'])
    ]]
    
    currency_symbol = '₱' if proposal.currency == 'PHP' else '$'
    
    for idx, item in enumerate(proposal.items.all(), start=1):
        table_data.append([
            Paragraph(str(idx), styles['TableText']),
            Paragraph(item.part_number, styles['TableText']),
            Paragraph(item.description, styles['TableText']),
            Paragraph(str(int(item.quantity)) if item.quantity % 1 == 0 else str(item.quantity), styles['TableText']),
            Paragraph(f"{currency_symbol} {item.unit_price:,.2f}", styles['TableText']),
            Paragraph(f"{currency_symbol} {item.amount:,.2f}", styles['TableText']),
            Paragraph(item.warranty or proposal.warranty, styles['TableText'])
        ])
    
    # Subtotal
    table_data.append([
        '', '', '', '', 
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
            '', '', '', '', 
            Paragraph(tax_label, styles['TableText']), 
            Paragraph(tax_amount_str, styles['TableText']), 
            ''
        ])

    # Total Investment Row
    table_data.append([
        '', '', '', '', 
        Paragraph("Total Investment", styles['TableHeader']), 
        Paragraph(f"{currency_symbol} {proposal.total_amount:,.2f}", styles['TableHeader']), 
        ''
    ])
    
    # Tighter widths to improve print margins and reduce empty space in TOTAL PRICE/WARRANTY
    col_widths = [0.45*inch, 1.1*inch, 2.4*inch, 0.5*inch, 1.0*inch, 1.1*inch, 0.95*inch]
    t = Table(table_data, colWidths=col_widths, repeatRows=1)
    
    # Styling
    table_style = [
        ('BACKGROUND', (0,0), (-1,0), MIC_RED), # Header Background
        ('TEXTCOLOR', (0,0), (-1,0), colors.white), # Header Text
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-2), 1, colors.black), # Grid for all except last row
        ('ALIGN', (2,1), (2,-2), 'LEFT'), # Description Left
        
        # Total Row Styling
        ('BACKGROUND', (4,-1), (5,-1), MIC_RED),
        ('TEXTCOLOR', (4,-1), (5,-1), colors.white),
        ('GRID', (4,-1), (5,-1), 1, MIC_RED),
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
        'professional': "To ensure we can commit the necessary resources to your project, please note that all confirmed Purchase Orders (POs) are considered final. Any cancellation will incur a fee equal to 100% of the total PO value.",
        'polite': "Please be advised that once a Purchase Order is confirmed, it is firm and cannot be cancelled without liability. Should a cancellation occur, the client agrees to a fee amounting to 100% of the PO value.",
        'partnership': "In order to best serve our clients and allocate our production capacity effectively, we treat all confirmed Purchase Orders as binding commitments. We trust you understand that any cancellation would require a charge covering the full value of the order."
    }
    
    cancellation_text = cancellation_texts.get(proposal.cancellation_terms, cancellation_texts.get('professional'))
    
    # Build Price Validity text with optional notes
    validity_parts = []
    validity_parts.append(f"Valid until {proposal.valid_until.strftime('%B %d, %Y') if proposal.valid_until else 'N/A'} only.")
    if getattr(proposal, 'validity_subject_to_prior_sale', False):
        validity_parts.append("Subject to Prior Sale.")
    if getattr(proposal, 'validity_availability_at_order', False):
        validity_parts.append("Availability at the time of Order.")
    validity_text = "<br/>".join(validity_parts)
    
    tc_data = [
        [Paragraph("Terms and Conditions:", tc_label), ''],
        [Paragraph("Price Validity", tc_label), Paragraph(validity_text, tc_style)],
        [Paragraph("Payment Terms", tc_label), Paragraph(proposal.payment_terms, tc_style)],
        [Paragraph("Cancellation", tc_label), Paragraph(cancellation_text, tc_style)],
    ]

    if proposal.include_bank_details:
        if proposal.currency == 'USD':
            bank_html = f"""
            <b>{proposal.usd_beneficiary_name}</b><br/>
            Beneficiary Address: {proposal.usd_beneficiary_address}<br/>
            Account Number: {proposal.usd_account_number}<br/>
            Bank Address: {proposal.usd_bank_address}<br/>
            SWIFT Code (BIC): {proposal.usd_swift_code}
            """.strip()
        else:
            bank_html = f"""
            <b>{proposal.php_account_name}</b><br/>
            {proposal.php_bank_name}<br/>
            Account Number: {proposal.php_account_number}<br/>
            Account Type: {proposal.php_account_type}<br/>
            Branch: {proposal.php_branch}
            """.strip()
        tc_data.append([Paragraph("Bank Details", tc_label), Paragraph(bank_html, tc_style)])

    tc_data.extend([
        [Paragraph("Delivery Lead time", tc_label), Paragraph(proposal.delivery_lead_time, tc_style)],
    ])
    
    if proposal.closing:
         tc_data.append([Paragraph("Other Terms", tc_label), Paragraph(proposal.closing.replace('\n', '<br/>'), tc_style)])

    tc_table = Table(tc_data, colWidths=[1.8*inch, 5.7*inch])
    tc_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (0,0), (0,-1), 'LEFT'),
        # Make the section header span both columns to avoid wrapping
        ('SPAN', (0,0), (1,0)),
        ('BOTTOMPADDING', (0,0), (1,0), 6),
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
    
    signature_img = None
    try:
        if hasattr(proposal.created_by, 'signature_image') and proposal.created_by.signature_image and proposal.created_by.signature_image.path:
            # Slightly smaller height and let the image sit closer to the line
            signature_img = Image(proposal.created_by.signature_image.path, width=2*inch, height=0.5*inch)
    except Exception:
        signature_img = None
    
    sig_data = [
        ['', 'Conforme:'],
        [signature_img or '', ''],
        ['__________________________', '__________________________'],
        [Paragraph(f"<b>{proposal.created_by.get_full_name()}</b><br/>Account Manager<br/>Mobile #: {proposal.created_by.mobile_number or ''}", styles['NormalSmall']), 
         Paragraph("Print Name & Sign<br/>Served as Order if signed by Authorized <br/>Representative", styles['NormalSmall'])]
    ]
    sig_table = Table(sig_data, colWidths=[3.5*inch, 4*inch])
    sig_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        # Place the signature image closer to the line below
        ('VALIGN', (0,1), (0,1), 'BOTTOM'),
        ('BOTTOMPADDING', (0,1), (-1,1), 6),
        ('TOPPADDING', (0,2), (-1,2), 2),
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
    if proposal.approval_required and proposal.approval_status != 'approved':
        messages.warning(request, f"Approval required before sending. Current status: {proposal.get_approval_status_display()}")
        return redirect('proposal_detail', pk=pk)
    
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
    
    # Build CC contacts list (main + additional with emails)
    try:
        from customers.models import CustomerContact
        additional_contacts = list(CustomerContact.objects.filter(customer=proposal.customer).order_by('-is_primary','name'))
    except Exception:
        additional_contacts = []
    cc_contacts = []
    # Main contact option
    if proposal.customer.email:
        cc_contacts.append({
            'label': f"{proposal.customer.contact_person_name or 'Main Contact'}",
            'email': proposal.customer.email
        })
    # Additional contact options
    for c in additional_contacts:
        if c.email:
            cc_contacts.append({
                'label': c.name,
                'email': c.email
            })
    
    if request.method == 'POST':
        # Get recipient emails (comma/semicolon separated supported)
        raw_to = request.POST.get('customer_emails') or request.POST.get('customer_email') or (proposal.contact_email or proposal.customer.email)
        to_list = []
        if raw_to:
            import re
            to_list = [e.strip() for e in re.split(r'[,\s;]+', raw_to) if e.strip()]
        # Fallback to single default if parsing produced none
        if not to_list and (proposal.contact_email or proposal.customer.email):
            to_list = [proposal.contact_email or proposal.customer.email]
        
        # Check for CC Supervisor
        cc_list = []
        if request.POST.get('cc_supervisor') == 'on' and supervisor_email:
            cc_list.append(supervisor_email)
        
        # Selected CC contacts
        for email in request.POST.getlist('cc_contact'):
            if email:
                cc_list.append(email.strip())
        
        # Free-form CCs (comma/semicolon separated)
        extra_cc = (request.POST.get('cc_emails') or '').strip()
        if extra_cc:
            import re
            pieces = re.split(r'[,\s;]+', extra_cc)
            for e in pieces:
                e = e.strip()
                if e:
                    cc_list.append(e)
        
        # Deduplicate and avoid duplicating To:
        lower_to = set([e.lower() for e in to_list])
        dedup_cc = []
        for i, e in enumerate(cc_list):
            if not e:
                continue
            el = e.lower()
            if el in lower_to:
                continue
            if e not in dedup_cc:
                dedup_cc.append(e)
        cc_list = dedup_cc
            
        # Generate PDF
        buffer = generate_pdf_buffer(proposal)
        
        # Attachments selected
        attach_ids = request.POST.getlist('attach_id')
        selected_attachments = proposal.attachments.filter(id__in=attach_ids)

        # Send Email
        subject = f"Proposal: {proposal.subject} - {proposal.proposal_number}"
        cover = (request.POST.get('cover_message') or '').strip()
        if not cover:
            cover = f"""Dear {proposal.contact_name or proposal.customer.contact_person_name},

Please find attached our proposal for {proposal.subject}.

Best regards,
{proposal.created_by.get_full_name()}"""
        message = cover
        email = EmailMessage(
            subject,
            message,
            request.user.email,
            to_list,
            cc=cc_list,
            reply_to=[request.user.email]
        )
        email.attach(f"{proposal.proposal_number}.pdf", buffer.getvalue(), 'application/pdf')
        for att in selected_attachments:
            if att.file:
                email.attach(att.display_name or att.file.name.split('/')[-1], att.file.read(), 'application/octet-stream')
        
        try:
            email.send()
            proposal.status = 'sent'
            proposal.save()
            
            # Log Activity
            log_sales_activity(proposal, request.user)
            
            # Update Funnel
            update_sales_funnel(proposal)
            
            recipients_str = ', '.join(to_list)
            msg = f"Proposal sent to {recipients_str}"
            if cc_list:
                msg += f" (CC: {', '.join(cc_list)})"
            messages.success(request, msg)
        except Exception as e:
            messages.error(request, f"Failed to send email: {str(e)}")
            
        return redirect('proposal_detail', pk=pk)
    
    return render(request, 'sales_proposals/proposal_email_confirm.html', {
        'proposal': proposal,
        'supervisor_email': supervisor_email,
        'cc_contacts': cc_contacts
    })

@login_required
def approvals_inbox(request):
    steps = ProposalApprovalStep.objects.filter(approver=request.user, status='pending').select_related('proposal', 'proposal__customer')
    return render(request, 'sales_proposals/approvals_inbox.html', {'steps': steps})

@login_required
def approve_proposal(request, pk):
    proposal = get_object_or_404(Proposal, pk=pk)
    step = ProposalApprovalStep.objects.filter(proposal=proposal, approver=request.user, status='pending').order_by('level').first()
    if not step:
        messages.error(request, 'No pending approval step assigned to you.')
        return redirect('proposal_detail', pk=pk)
    if request.method == 'POST':
        step.status = 'approved'
        step.decided_at = timezone.now()
        step.comment = request.POST.get('comment', '')
        step.save()
        next_step = ProposalApprovalStep.objects.filter(proposal=proposal, status='pending').order_by('level').first()
        if not next_step:
            proposal.approval_status = 'approved'
            proposal.approved_at = timezone.now()
            proposal.save()
            messages.success(request, 'Proposal fully approved.')
        else:
            messages.success(request, 'Step approved. Awaiting next approver.')
        return redirect('proposal_detail', pk=pk)
    return render(request, 'sales_proposals/approve_confirm.html', {'proposal': proposal})

@login_required
def reject_proposal(request, pk):
    proposal = get_object_or_404(Proposal, pk=pk)
    step = ProposalApprovalStep.objects.filter(proposal=proposal, approver=request.user, status='pending').order_by('level').first()
    if not step:
        messages.error(request, 'No pending approval step assigned to you.')
        return redirect('proposal_detail', pk=pk)
    if request.method == 'POST':
        step.status = 'rejected'
        step.decided_at = timezone.now()
        step.comment = request.POST.get('comment', '')
        step.save()
        proposal.approval_status = 'rejected'
        proposal.save()
        messages.warning(request, 'Proposal rejected.')
        return redirect('proposal_detail', pk=pk)
    return render(request, 'sales_proposals/reject_confirm.html', {'proposal': proposal})

def _is_exec(user):
    return user.role in ['admin', 'president', 'vp', 'avp', 'gm']

@login_required
def approval_tier_list(request):
    if not _is_exec(request.user):
        messages.error(request, 'Not authorized')
        return redirect('proposal_list')
    tiers = ProposalApprovalTier.objects.all()
    return render(request, 'sales_proposals/approval_tier_list.html', {'tiers': tiers})

@login_required
def approval_tier_create(request):
    if not _is_exec(request.user):
        messages.error(request, 'Not authorized')
        return redirect('proposal_list')
    if request.method == 'POST':
        form = ProposalApprovalTierForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Approval tier created')
            return redirect('approval_tier_list')
    else:
        form = ProposalApprovalTierForm()
    return render(request, 'sales_proposals/approval_tier_form.html', {'form': form, 'title': 'Create Approval Tier'})

@login_required
def approval_tier_edit(request, pk):
    if not _is_exec(request.user):
        messages.error(request, 'Not authorized')
        return redirect('proposal_list')
    tier = get_object_or_404(ProposalApprovalTier, pk=pk)
    if request.method == 'POST':
        form = ProposalApprovalTierForm(request.POST, instance=tier)
        if form.is_valid():
            form.save()
            messages.success(request, 'Approval tier updated')
            return redirect('approval_tier_list')
    else:
        form = ProposalApprovalTierForm(instance=tier)
    return render(request, 'sales_proposals/approval_tier_form.html', {'form': form, 'title': 'Edit Approval Tier'})

@login_required
def approval_tier_delete(request, pk):
    if not _is_exec(request.user):
        messages.error(request, 'Not authorized')
        return redirect('proposal_list')
    tier = get_object_or_404(ProposalApprovalTier, pk=pk)
    if request.method == 'POST':
        tier.delete()
        messages.success(request, 'Approval tier deleted')
        return redirect('approval_tier_list')
    return render(request, 'sales_proposals/approval_tier_confirm_delete.html', {'tier': tier})

@login_required
def approval_tier_export(request):
    if not _is_exec(request.user):
        messages.error(request, 'Not authorized')
        return redirect('proposal_list')
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="approval_tiers_export.csv"'
    writer = csv.writer(response)
    writer.writerow(['name', 'min_amount_php', 'max_amount_php', 'chain', 'order', 'active'])
    for t in ProposalApprovalTier.objects.all().order_by('order', 'min_amount_php'):
        writer.writerow([t.name or '', str(t.min_amount_php), '' if t.max_amount_php is None else str(t.max_amount_php), t.chain, t.order, 'true' if t.active else 'false'])
    return response

@login_required
def approval_tier_template(request):
    if not _is_exec(request.user):
        messages.error(request, 'Not authorized')
        return redirect('proposal_list')
    template_path = os.path.join(settings.BASE_DIR, 'sales_proposals', 'sample_templates', 'approval_tiers_template.csv')
    return FileResponse(open(template_path, 'rb'), as_attachment=True, filename='approval_tiers_template.csv')

@login_required
def approval_tier_import(request):
    if not _is_exec(request.user):
        messages.error(request, 'Not authorized')
        return redirect('proposal_list')
    if request.method == 'POST':
        form = ProposalApprovalTierImportForm(request.POST, request.FILES)
        if form.is_valid():
            f = form.cleaned_data['file']
            replace = form.cleaned_data['replace_existing']
            decoded = f.read().decode('utf-8').splitlines()
            reader = csv.DictReader(decoded)
            rows = list(reader)
            if replace:
                ProposalApprovalTier.objects.all().delete()
            created = 0
            for r in rows:
                name = (r.get('name') or '').strip()
                min_amt = Decimal((r.get('min_amount_php') or '0').strip() or '0')
                max_raw = (r.get('max_amount_php') or '').strip()
                max_amt = Decimal(max_raw) if max_raw not in ['', None] else None
                chain = (r.get('chain') or '').strip()
                order = int((r.get('order') or '0').strip() or '0')
                active_val = (r.get('active') or '').strip().lower()
                active = active_val in ['1', 'true', 'yes', 'y']
                ProposalApprovalTier.objects.create(name=name, min_amount_php=min_amt, max_amount_php=max_amt, chain=chain, order=order, active=active)
                created += 1
            messages.success(request, f'Imported {created} tiers')
            return redirect('approval_tier_list')
    else:
        form = ProposalApprovalTierImportForm()
    return render(request, 'sales_proposals/approval_tier_import.html', {'form': form})

@login_required
def approval_tier_seed_defaults(request):
    if not _is_exec(request.user):
        messages.error(request, 'Not authorized')
        return redirect('proposal_list')
    if request.method != 'POST':
        return redirect('approval_tier_list')
    seeds = [
        dict(name='Supervisor Tier', min=Decimal('500000'), max=Decimal('999999'), chain='supervisor', order=1, active=True),
        dict(name='Supervisor + ASM', min=Decimal('1000000'), max=Decimal('2999999'), chain='supervisor,asm', order=2, active=True),
        dict(name='Sup + ASM + AVP/GM', min=Decimal('3000000'), max=None, chain='supervisor,asm,avp_or_gm', order=3, active=True),
    ]
    created, updated = 0, 0
    for s in seeds:
        qs = ProposalApprovalTier.objects.filter(min_amount_php=s['min'], chain=s['chain'])
        if s['max'] is None:
            qs = qs.filter(max_amount_php__isnull=True)
        else:
            qs = qs.filter(max_amount_php=s['max'])
        obj = qs.first()
        if obj:
            obj.name = s['name']
            obj.order = s['order']
            obj.active = s['active']
            obj.save()
            updated += 1
        else:
            ProposalApprovalTier.objects.create(
                name=s['name'],
                min_amount_php=s['min'],
                max_amount_php=s['max'],
                chain=s['chain'],
                order=s['order'],
                active=s['active'],
            )
            created += 1
    messages.success(request, f'Default tiers seeded. Created: {created}, Updated: {updated}.')
    return redirect('approval_tier_list')

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
