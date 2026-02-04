from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Sum, Count, F
from django.utils import timezone
from .models import SalesFunnel
from .forms import SalesFunnelForm, FunnelFilterForm, BulkUpdateStageForm
from users.models import User
from teams.models import Team, Group, TeamMembership
from customers.models import Customer
import csv
from io import TextIOWrapper, StringIO
from decimal import Decimal
from datetime import datetime


def can_access_funnel(user):
    """Check if user can access sales funnel features"""
    return user.role in ['salesperson', 'supervisor', 'teamlead', 'asm', 'avp', 'admin', 'president', 'gm', 'vp']

def is_salesperson(user):
    return user.role == 'salesperson'

def is_manager(user):
    return user.role in ['supervisor', 'teamlead', 'asm', 'avp', 'admin', 'president', 'gm', 'vp']

def is_exec_admin(user):
    return user.role in ['admin', 'president', 'gm', 'vp']


@login_required
@user_passes_test(can_access_funnel)
def funnel_dashboard(request):
    """Main dashboard view for sales funnel"""
    user = request.user
    view_mode = request.GET.get('view', 'card')
    
    # Get funnel entries based on user role
    if user.role == 'salesperson':
        funnel_entries = SalesFunnel.objects.filter(
            salesperson=user,
            is_active=True,
            is_closed=False
        )
    elif user.role == 'supervisor':
        # Supervisor can see entries from their groups
        groups = Group.objects.filter(supervisor=user)
        salespeople_ids = TeamMembership.objects.filter(group__in=groups).values_list('user_id', flat=True)
        funnel_entries = SalesFunnel.objects.filter(
            salesperson_id__in=salespeople_ids,
            is_active=True,
            is_closed=False
        )
    elif user.role == 'teamlead':
        # Teamlead can see entries from their assigned group
        teamlead_groups = Group.objects.filter(teamlead=user)
        salespeople_ids = TeamMembership.objects.filter(group__in=teamlead_groups).values_list('user_id', flat=True)
        funnel_entries = SalesFunnel.objects.filter(
            salesperson_id__in=salespeople_ids,
            is_active=True,
            is_closed=False
        )
    elif user.role == 'asm':
        # ASM can see entries from their teams
        asm_teams = user.asm_teams.all()
        groups = Group.objects.filter(team__in=asm_teams)
        salespeople_ids = TeamMembership.objects.filter(group__in=groups).values_list('user_id', flat=True)
        funnel_entries = SalesFunnel.objects.filter(
            salesperson_id__in=salespeople_ids,
            is_active=True,
            is_closed=False
        )
    elif user.role == 'avp':
        # AVP can see entries from their teams
        teams = Team.objects.filter(avp=user)
        groups = Group.objects.filter(team__in=teams)
        salespeople_ids = TeamMembership.objects.filter(group__in=groups).values_list('user_id', flat=True)
        funnel_entries = SalesFunnel.objects.filter(
            salesperson_id__in=salespeople_ids,
            is_active=True,
            is_closed=False
        )
    else:
        # Executives and admins can see all entries
        funnel_entries = SalesFunnel.objects.filter(
            is_active=True,
            is_closed=False
        )
    
    # Apply filters if provided
    filter_form = FunnelFilterForm(request.GET, user=user)
    if filter_form.is_valid():
        stage = filter_form.cleaned_data.get('stage')
        salesperson = filter_form.cleaned_data.get('salesperson')
        min_amount = filter_form.cleaned_data.get('min_amount')
        date_from = filter_form.cleaned_data.get('date_from')
        date_to = filter_form.cleaned_data.get('date_to')
        
        if stage:
            funnel_entries = funnel_entries.filter(stage=stage)
        if salesperson:
            funnel_entries = funnel_entries.filter(salesperson=salesperson)
        if min_amount is not None:
            funnel_entries = funnel_entries.filter(retail__gte=min_amount)
        if date_from:
            funnel_entries = funnel_entries.filter(date_created__gte=date_from)
        if date_to:
            funnel_entries = funnel_entries.filter(date_created__lte=date_to)
    
    # Organize entries by stage
    quoted_entries = funnel_entries.filter(stage='quoted').select_related('salesperson', 'customer')
    closable_entries = funnel_entries.filter(stage='closable').select_related('salesperson', 'customer')
    project_entries = funnel_entries.filter(stage='project').select_related('salesperson', 'customer')
    services_entries = funnel_entries.filter(stage='services').select_related('salesperson', 'customer')
    
    # Get closed deals statistics based on same user role logic
    if user.role == 'salesperson':
        closed_deals = SalesFunnel.objects.filter(salesperson=user, is_closed=True)
    elif user.role == 'supervisor':
        groups = Group.objects.filter(supervisor=user)
        salespeople_ids = TeamMembership.objects.filter(group__in=groups).values_list('user_id', flat=True)
        closed_deals = SalesFunnel.objects.filter(salesperson_id__in=salespeople_ids, is_closed=True)
    elif user.role == 'teamlead':
        teamlead_groups = Group.objects.filter(teamlead=user)
        salespeople_ids = TeamMembership.objects.filter(group__in=teamlead_groups).values_list('user_id', flat=True)
        closed_deals = SalesFunnel.objects.filter(salesperson_id__in=salespeople_ids, is_closed=True)
    elif user.role == 'asm':
        asm_teams = user.asm_teams.all()
        groups = Group.objects.filter(team__in=asm_teams)
        salespeople_ids = TeamMembership.objects.filter(group__in=groups).values_list('user_id', flat=True)
        closed_deals = SalesFunnel.objects.filter(salesperson_id__in=salespeople_ids, is_closed=True)
    elif user.role == 'avp':
        teams = Team.objects.filter(avp=user)
        groups = Group.objects.filter(team__in=teams)
        salespeople_ids = TeamMembership.objects.filter(group__in=groups).values_list('user_id', flat=True)
        closed_deals = SalesFunnel.objects.filter(salesperson_id__in=salespeople_ids, is_closed=True)
    else:
        closed_deals = SalesFunnel.objects.filter(is_closed=True)
    
    # Calculate won/lost statistics
    won_deals = closed_deals.filter(deal_outcome='won')
    lost_deals = closed_deals.filter(deal_outcome='lost')
    total_closed = closed_deals.count()
    
    won_stats = {
        'count': won_deals.count(),
        'total_value': won_deals.aggregate(Sum('retail'))['retail__sum'] or 0,
    }
    lost_stats = {
        'count': lost_deals.count(),
        'total_value': lost_deals.aggregate(Sum('retail'))['retail__sum'] or 0,
    }
    win_rate = (won_stats['count'] / total_closed * 100) if total_closed > 0 else 0
    
    # Calculate statistics
    stats = {
        'total_entries': funnel_entries.count(),
        'total_value': funnel_entries.aggregate(Sum('retail'))['retail__sum'] or 0,
        'total_profit': sum(entry.profit for entry in funnel_entries),
        'quoted_count': quoted_entries.count(),
        'closable_count': closable_entries.count(),
        'project_count': project_entries.count(),
        'services_count': services_entries.count(),
        # Add won/lost stats
        'won_count': won_stats['count'],
        'lost_count': lost_stats['count'],
        'total_closed': total_closed,
        'win_rate': win_rate,
        'won_value': won_stats['total_value'],
        'lost_value': lost_stats['total_value'],
    }
    # Stage totals for table view
    stage_totals = {
        'quoted': {
            'retail': quoted_entries.aggregate(total=Sum('retail'))['total'] or 0,
            'profit': quoted_entries.aggregate(total=Sum(F('retail') - F('cost')))['total'] or 0,
        },
        'closable': {
            'retail': closable_entries.aggregate(total=Sum('retail'))['total'] or 0,
            'profit': closable_entries.aggregate(total=Sum(F('retail') - F('cost')))['total'] or 0,
        },
        'project': {
            'retail': project_entries.aggregate(total=Sum('retail'))['total'] or 0,
            'profit': project_entries.aggregate(total=Sum(F('retail') - F('cost')))['total'] or 0,
        },
        'services': {
            'retail': services_entries.aggregate(total=Sum('retail'))['total'] or 0,
            'profit': services_entries.aggregate(total=Sum(F('retail') - F('cost')))['total'] or 0,
        },
    }
    
    context = {
        'quoted_entries': quoted_entries,
        'closable_entries': closable_entries,
        'project_entries': project_entries,
        'services_entries': services_entries,
        'stats': stats,
        'stage_totals': stage_totals,
        'filter_form': filter_form,
        'can_add': user.role == 'salesperson',
        'can_edit_all': user.role in ['admin', 'supervisor', 'asm', 'avp'],
        'view_mode': view_mode,
        'show_actions': view_mode != 'table',
    }
    
    return render(request, 'sales_funnel/dashboard.html', context)


@login_required
@user_passes_test(is_manager)
def export_funnel_report(request):
    user = request.user
    if user.role == 'salesperson':
        return redirect('sales_funnel:dashboard')

    if user.role == 'supervisor':
        groups = Group.objects.filter(supervisor=user)
        salespeople_ids = TeamMembership.objects.filter(group__in=groups).values_list('user_id', flat=True)
        qs = SalesFunnel.objects.filter(salesperson_id__in=salespeople_ids, is_active=True, is_closed=False)
    elif user.role == 'teamlead':
        teamlead_groups = Group.objects.filter(teamlead=user)
        salespeople_ids = TeamMembership.objects.filter(group__in=teamlead_groups).values_list('user_id', flat=True)
        qs = SalesFunnel.objects.filter(salesperson_id__in=salespeople_ids, is_active=True, is_closed=False)
    elif user.role == 'asm':
        asm_teams = user.asm_teams.all()
        groups = Group.objects.filter(team__in=asm_teams)
        salespeople_ids = TeamMembership.objects.filter(group__in=groups).values_list('user_id', flat=True)
        qs = SalesFunnel.objects.filter(salesperson_id__in=salespeople_ids, is_active=True, is_closed=False)
    elif user.role == 'avp':
        teams = Team.objects.filter(avp=user)
        groups = Group.objects.filter(team__in=teams)
        salespeople_ids = TeamMembership.objects.filter(group__in=groups).values_list('user_id', flat=True)
        qs = SalesFunnel.objects.filter(salesperson_id__in=salespeople_ids, is_active=True, is_closed=False)
    else:
        qs = SalesFunnel.objects.filter(is_active=True, is_closed=False)

    form = FunnelFilterForm(request.GET, user=user)
    if form.is_valid():
        stage = form.cleaned_data.get('stage')
        salesperson = form.cleaned_data.get('salesperson')
        min_amount = form.cleaned_data.get('min_amount')
        date_from = form.cleaned_data.get('date_from')
        date_to = form.cleaned_data.get('date_to')
        if stage:
            qs = qs.filter(stage=stage)
        if salesperson:
            qs = qs.filter(salesperson=salesperson)
        if min_amount is not None:
            qs = qs.filter(retail__gte=min_amount)
        if date_from:
            qs = qs.filter(date_created__gte=date_from)
        if date_to:
            qs = qs.filter(date_created__lte=date_to)

    response = HttpResponse(content_type='text/csv')
    filename = f"funnel_export_{timezone.now().strftime('%Y%m%d')}.csv"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    writer = csv.writer(response)
    writer.writerow([
        'Date', 'Company', 'Stage', 'Retail', 'Cost', 'Profit', 'Salesperson', 'Customer', 'Expected Close', 'Probability', 'Notes'
    ])
    for e in qs.select_related('salesperson', 'customer').order_by('-date_created'):
        writer.writerow([
            e.date_created.strftime('%Y-%m-%d'),
            e.company_name,
            e.get_stage_display(),
            f"{e.retail}",
            f"{e.cost}",
            f"{e.profit}",
            e.salesperson.username,
            e.customer.full_name if e.customer else '',
            e.expected_close_date.strftime('%Y-%m-%d') if e.expected_close_date else '',
            e.probability,
            e.notes,
        ])
    return response


@login_required
@user_passes_test(is_salesperson)
def add_funnel_entry(request):
    """Add a new funnel entry (salesperson only)"""
    if request.method == 'POST':
        form = SalesFunnelForm(request.POST, user=request.user)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.salesperson = request.user
            entry.save()
            messages.success(request, 'Funnel entry added successfully!')
            return redirect('sales_funnel:dashboard')
    else:
        form = SalesFunnelForm(user=request.user)
    
    return render(request, 'sales_funnel/add_entry.html', {'form': form})


@login_required
@user_passes_test(can_access_funnel)
def edit_funnel_entry(request, entry_id):
    """Edit a funnel entry"""
    entry = get_object_or_404(SalesFunnel, id=entry_id)
    
    # Check permissions
    if request.user.role == 'salesperson' and entry.salesperson != request.user:
        messages.error(request, 'You can only edit your own funnel entries.')
        return redirect('sales_funnel:dashboard')
    
    if request.method == 'POST':
        form = SalesFunnelForm(request.POST, instance=entry, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Funnel entry updated successfully!')
            return redirect('sales_funnel:dashboard')
    else:
        form = SalesFunnelForm(instance=entry, user=request.user)
    
    return render(request, 'sales_funnel/edit_entry.html', {
        'form': form,
        'entry': entry
    })


@login_required
@user_passes_test(can_access_funnel)
def delete_funnel_entry(request, entry_id):
    """Delete a funnel entry"""
    entry = get_object_or_404(SalesFunnel, id=entry_id)
    
    # Check permissions
    if request.user.role == 'salesperson' and entry.salesperson != request.user:
        messages.error(request, 'You can only delete your own funnel entries.')
        return redirect('sales_funnel:dashboard')
    
    if request.method == 'POST':
        company_name = entry.company_name
        entry.delete()
        messages.success(request, f'Funnel entry for "{company_name}" deleted successfully!')
    
    return redirect('sales_funnel:dashboard')


@login_required
@user_passes_test(can_access_funnel)
def update_entry_stage(request, entry_id):
    """AJAX endpoint to update funnel entry stage"""
    if request.method == 'POST':
        entry = get_object_or_404(SalesFunnel, id=entry_id)
        
        # Check permissions
        if request.user.role == 'salesperson' and entry.salesperson != request.user:
            return JsonResponse({
                'success': False,
                'message': 'Permission denied'
            })
        
        new_stage = request.POST.get('stage')
        if new_stage in ['quoted', 'closable', 'project', 'services']:
            if new_stage in ['project', 'services']:
                # Enforce threshold-based classification
                from decimal import Decimal
                threshold = Decimal('500000')
                entry.stage = 'project' if entry.retail >= threshold else 'services'
            else:
                entry.stage = new_stage
            entry.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Entry moved to {entry.get_stage_display()}',
                'stage': entry.stage,
                'stage_display': entry.get_stage_display(),
                'stage_color': entry.stage_color
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'Invalid stage'
            })
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})


@login_required
@user_passes_test(can_access_funnel)
def close_entry(request, entry_id):
    """Mark a funnel entry as closed (won or lost)"""
    entry = get_object_or_404(SalesFunnel, id=entry_id)
    
    # Check permissions
    if request.user.role == 'salesperson' and entry.salesperson != request.user:
        messages.error(request, 'You can only close your own funnel entries.')
        return redirect('sales_funnel:dashboard')
    
    if request.method == 'POST':
        won = request.POST.get('won') == 'true'
        entry.is_closed = True
        entry.deal_outcome = 'won' if won else 'lost'
        entry.closed_date = timezone.now().date()
        entry.notes = f"{entry.notes}\n\nClosed on {entry.closed_date} - {'WON' if won else 'LOST'}".strip()
        entry.save()
        
        status = 'won' if won else 'lost'
        messages.success(request, f'Deal for "{entry.company_name}" marked as {status}!')
    
    return redirect('sales_funnel:dashboard')


@login_required
@user_passes_test(can_access_funnel)
def deals_history(request):
    """View to show comprehensive won/lost deal statistics"""
    user = request.user
    
    # Get closed deals based on user role - similar logic to funnel_dashboard
    if user.role == 'salesperson':
        closed_deals = SalesFunnel.objects.filter(
            salesperson=user,
            is_closed=True
        )
    elif user.role == 'supervisor':
        groups = Group.objects.filter(supervisor=user)
        salespeople_ids = TeamMembership.objects.filter(group__in=groups).values_list('user_id', flat=True)
        closed_deals = SalesFunnel.objects.filter(
            salesperson_id__in=salespeople_ids,
            is_closed=True
        )
    elif user.role == 'teamlead':
        teamlead_groups = Group.objects.filter(teamlead=user)
        salespeople_ids = TeamMembership.objects.filter(group__in=teamlead_groups).values_list('user_id', flat=True)
        closed_deals = SalesFunnel.objects.filter(
            salesperson_id__in=salespeople_ids,
            is_closed=True
        )
    elif user.role == 'asm':
        asm_teams = user.asm_teams.all()
        groups = Group.objects.filter(team__in=asm_teams)
        salespeople_ids = TeamMembership.objects.filter(group__in=groups).values_list('user_id', flat=True)
        closed_deals = SalesFunnel.objects.filter(
            salesperson_id__in=salespeople_ids,
            is_closed=True
        )
    elif user.role == 'avp':
        teams = Team.objects.filter(avp=user)
        groups = Group.objects.filter(team__in=teams)
        salespeople_ids = TeamMembership.objects.filter(group__in=groups).values_list('user_id', flat=True)
        closed_deals = SalesFunnel.objects.filter(
            salesperson_id__in=salespeople_ids,
            is_closed=True
        )
    else:
        # Executives and admins can see all closed deals
        closed_deals = SalesFunnel.objects.filter(is_closed=True)
    
    # Apply date filters if provided
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if date_from:
        closed_deals = closed_deals.filter(closed_date__gte=date_from)
    if date_to:
        closed_deals = closed_deals.filter(closed_date__lte=date_to)
    
    # Separate won and lost deals
    won_deals = closed_deals.filter(deal_outcome='won').select_related('salesperson', 'customer')
    lost_deals = closed_deals.filter(deal_outcome='lost').select_related('salesperson', 'customer')
    
    # Calculate overall statistics
    won_stats = {
        'count': won_deals.count(),
        'total_value': won_deals.aggregate(Sum('retail'))['retail__sum'] or 0,
        'total_cost': won_deals.aggregate(Sum('cost'))['cost__sum'] or 0,
    }
    won_stats['total_profit'] = won_stats['total_value'] - won_stats['total_cost']
    
    # Calculate profit margin percentage
    if won_stats['total_value'] > 0:
        won_stats['profit_margin'] = (won_stats['total_profit'] / won_stats['total_value']) * 100
    else:
        won_stats['profit_margin'] = 0
    
    lost_stats = {
        'count': lost_deals.count(),
        'total_value': lost_deals.aggregate(Sum('retail'))['retail__sum'] or 0,
        'total_cost': lost_deals.aggregate(Sum('cost'))['cost__sum'] or 0,
    }
    lost_stats['total_profit'] = lost_stats['total_value'] - lost_stats['total_cost']
    
    # Calculate win rate and averages
    total_closed = won_stats['count'] + lost_stats['count']
    win_rate = (won_stats['count'] / total_closed * 100) if total_closed > 0 else 0
    
    # Calculate average values
    total_value_all = won_stats['total_value'] + lost_stats['total_value']
    average_deal_value = (total_value_all / total_closed) if total_closed > 0 else 0
    average_won_deal = (won_stats['total_value'] / won_stats['count']) if won_stats['count'] > 0 else 0
    
    # Get top performing salespeople (if user can see multiple salespeople)
    top_salespeople = []
    if user.role in ['supervisor', 'teamlead', 'asm', 'avp', 'admin', 'president', 'gm', 'vp']:
        from django.db.models import Count as DbCount
        salespeople_stats = closed_deals.values(
            'salesperson__username',
            'salesperson__first_name', 
            'salesperson__last_name'
        ).annotate(
            won_count=DbCount('id', filter=Q(deal_outcome='won')),
            lost_count=DbCount('id', filter=Q(deal_outcome='lost')),
            total_won_value=Sum('retail', filter=Q(deal_outcome='won')),
            total_lost_value=Sum('retail', filter=Q(deal_outcome='lost'))
        ).order_by('-won_count')[:10]
        
        # Calculate win rate for each salesperson
        top_salespeople = []
        for sp in salespeople_stats:
            total_deals = sp['won_count'] + sp['lost_count']
            win_rate = (sp['won_count'] / total_deals * 100) if total_deals > 0 else 0
            sp['total_deals'] = total_deals
            sp['win_rate'] = win_rate
            sp['total_won_value'] = sp['total_won_value'] or 0
            sp['total_lost_value'] = sp['total_lost_value'] or 0
            top_salespeople.append(sp)
    
    # Recent won and lost deals
    recent_won = won_deals.order_by('-closed_date')[:10]
    recent_lost = lost_deals.order_by('-closed_date')[:10]
    
    context = {
        'won_stats': won_stats,
        'lost_stats': lost_stats,
        'win_rate': win_rate,
        'total_closed': total_closed,
        'recent_won': recent_won,
        'recent_lost': recent_lost,
        'top_salespeople': top_salespeople,
        'date_from': date_from,
        'date_to': date_to,
        'can_see_all_salespeople': user.role in ['supervisor', 'teamlead', 'asm', 'avp', 'admin', 'president', 'gm', 'vp'],
        'average_deal_value': average_deal_value,
        'average_won_deal': average_won_deal,
    }
    
    return render(request, 'sales_funnel/deals_history.html', context)


@login_required
@user_passes_test(is_salesperson)
def import_funnel_entries(request):
    if request.method == 'POST':
        file = request.FILES.get('csv_file')
        if not file:
            messages.error(request, 'Please select a CSV file to upload.')
            return redirect('sales_funnel:import_entries')

        try:
            # Read file content
            content = file.read()
            
            # Try decoding with different encodings
            decoded_file = None
            encoding_error = None
            
            for encoding in ['utf-8-sig', 'utf-8', 'cp1252', 'latin-1', 'utf-16']:
                try:
                    decoded_file = content.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue
            
            if decoded_file is None:
                messages.error(request, 'Unable to read the CSV file. Unsupported encoding.')
                return redirect('sales_funnel:import_entries')

            # Use StringIO for CSV reading
            csv_file = StringIO(decoded_file)
            
            # Try to sniff dialect (delimiter)
            try:
                sample = decoded_file[:4096]
                dialect = csv.Sniffer().sniff(sample, delimiters=',;\t')
            except csv.Error:
                dialect = 'excel'
            
            csv_file.seek(0)
            
            # Read headers to normalize them
            reader = csv.reader(csv_file, dialect=dialect)
            try:
                headers = next(reader)
            except StopIteration:
                messages.error(request, 'CSV file is empty.')
                return redirect('sales_funnel:import_entries')
                
            # Normalize headers: strip whitespace and convert to lowercase
            normalized_headers = [h.strip().lower() for h in headers]
            
            # Create DictReader with normalized headers
            rows = csv.DictReader(csv_file, fieldnames=normalized_headers, dialect=dialect)
        except Exception as e:
            messages.error(request, f'Error reading CSV file: {str(e)}')
            return redirect('sales_funnel:import_entries')

        stage_map = {
            'newly quoted': 'quoted',
            'quoted': 'quoted',
            'closable this month': 'closable',
            'closable': 'closable',
            'project based': 'project',
            'project': 'project',
            'services': 'services',
        }

        def parse_date(value):
            if not value:
                return None
            for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%b %d %Y'):
                try:
                    return datetime.strptime(value.strip(), fmt).date()
                except Exception:
                    continue
            return None

        def parse_decimal(value):
            if value is None:
                return Decimal('0')
            s = str(value).replace('₱', '').replace(',', '').replace(' ', '').strip()
            if not s:
                return Decimal('0')
            try:
                return Decimal(s)
            except Exception:
                return None

        created = 0
        failed = 0
        errors = []

        for idx, row in enumerate(rows, start=1):
            getv = lambda k: row.get(k.strip().lower())
            date_created = getv('Date Created')
            company_name = getv('Company Name')
            requirement_description = getv('Requirement Description')
            cost_val = getv('Cost')
            retail_val = getv('Retail')
            stage_val = getv('Stage')
            customer_name = getv('Customer')
            expected_close_date = getv('Expected Close Date')
            probability_val = getv('Probability')
            notes_val = getv('Notes')

            if not all([date_created, company_name, requirement_description, cost_val, retail_val, stage_val]):
                failed += 1
                errors.append(f'Row {idx}: missing required fields')
                continue

            dc = parse_date(date_created)
            if not dc:
                failed += 1
                errors.append(f'Row {idx}: invalid Date Created')
                continue

            cost = parse_decimal(cost_val)
            retail = parse_decimal(retail_val)
            if cost is None or retail is None:
                failed += 1
                errors.append(f'Row {idx}: invalid numeric Cost/Retail')
                continue

            stage_key = str(stage_val).strip().lower()
            stage = stage_map.get(stage_key)
            if stage not in ['quoted', 'closable', 'project', 'services']:
                failed += 1
                errors.append(f'Row {idx}: invalid Stage')
                continue

            prob = 50
            if probability_val not in [None, '']:
                try:
                    val = str(probability_val).replace('%', '').strip()
                    prob = int(float(val))
                except Exception:
                    failed += 1
                    errors.append(f'Row {idx}: invalid Probability')
                    continue
                if prob < 0 or prob > 100:
                    failed += 1
                    errors.append(f'Row {idx}: Probability out of range')
                    continue

            if retail < cost:
                failed += 1
                errors.append(f'Row {idx}: Retail less than Cost')
                continue

            customer_obj = None
            if customer_name:
                customer_obj = Customer.objects.filter(company_name__iexact=customer_name.strip(), is_active=True).first()

            exp_close = parse_date(expected_close_date) if expected_close_date else None

            entry = SalesFunnel(
                date_created=dc,
                company_name=company_name.strip(),
                requirement_description=str(requirement_description).strip(),
                cost=cost,
                retail=retail,
                stage=('project' if stage in ['project','services'] and retail is not None and retail >= Decimal('500000') else ('services' if stage in ['project','services'] else stage)),
                salesperson=request.user,
                customer=customer_obj,
                expected_close_date=exp_close,
                probability=prob,
                notes=(str(notes_val).strip() if notes_val else ''),
            )

            try:
                entry.save()
                created += 1
            except Exception as e:
                failed += 1
                errors.append(f'Row {idx}: {str(e)[:200]}')

        if created:
            messages.success(request, f'Imported {created} funnel entries.')
        if failed:
            preview = '; '.join(errors[:5])
            if preview:
                messages.warning(request, f'{failed} rows failed. {preview}')
        return redirect('sales_funnel:dashboard')

    return render(request, 'sales_funnel/import_entries.html')

@login_required
@user_passes_test(is_exec_admin)
def normalize_funnel_stages(request):
    threshold = Decimal('500000')
    qs = SalesFunnel.objects.filter(is_active=True, is_closed=False, stage__in=['project', 'services'])
    to_project = 0
    to_services = 0
    unchanged = 0
    for e in qs.only('id', 'retail', 'stage'):
        desired = 'project' if (e.retail or Decimal('0')) >= threshold else 'services'
        if e.stage != desired:
            e.stage = desired
            e.save(update_fields=['stage', 'updated_at'])
            if desired == 'project':
                to_project += 1
            else:
                to_services += 1
        else:
            unchanged += 1
    messages.success(request, f'Normalized stages: {to_project} → Project, {to_services} → Services, {unchanged} unchanged.')
    return redirect('sales_funnel:dashboard')


@login_required
@user_passes_test(is_salesperson)
def download_sample_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="funnel_import_sample.csv"'
    writer = csv.writer(response)
    writer.writerow([
        'Date Created', 'Company Name', 'Requirement Description', 'Cost', 'Retail', 'Stage',
        'Customer', 'Expected Close Date', 'Probability', 'Notes'
    ])
    writer.writerow([
        '2025-11-01', 'Water District Lipa', 'Laptop i7 16GB RAM 1TB SSD x 10', '450000', '650000', 'Newly Quoted',
        'Water District Lipa', '2025-12-15', '50', 'Include extended warranty'
    ])
    writer.writerow([
        '2025-10-15', 'San Miguel Corporation', 'HP Workstation', '500000', '750000', 'Closable This Month',
        'San Miguel Corporation', '2025-11-30', '70', ''
    ])
    writer.writerow([
        '2025-09-20', 'ABC Engineering', 'Project-based deployment, phased', '300000', '500000', 'Project Based',
        '', '', '40', 'Phase 1 pending approval'
    ])
    return response


@login_required
@user_passes_test(is_exec_admin)
def clear_stage_entries(request):
    """Admin/executive-only: clear entries by stage for a given month."""
    from calendar import monthrange
    today = timezone.now().date()
    default_month = today.strftime('%Y-%m')
    if request.method == 'POST':
        stage = request.POST.get('stage')
        month_str = request.POST.get('month') or default_month
        try:
            year, month = map(int, month_str.split('-'))
            start_date = datetime(year, month, 1).date()
            end_day = monthrange(year, month)[1]
            end_date = datetime(year, month, end_day).date()
        except Exception:
            messages.error(request, 'Invalid month format. Use YYYY-MM.')
            return redirect('sales_funnel:clear_stage')
        if stage not in ['quoted', 'closable', 'project', 'services']:
            messages.error(request, 'Invalid stage.')
            return redirect('sales_funnel:clear_stage')
        qs = SalesFunnel.objects.filter(stage=stage, date_created__gte=start_date, date_created__lte=end_date)
        # Only remove active/open entries
        qs = qs.filter(is_closed=False)
        count = qs.count()
        qs.delete()
        messages.success(request, f'Cleared {count} entries from "{dict(SalesFunnel.FUNNEL_STAGES).get(stage)}" for {month_str}.')
        return redirect('sales_funnel:dashboard')
    return render(request, 'sales_funnel/clear_stage.html', {'default_month': default_month})
