from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum, Avg
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json
import csv
from datetime import datetime, timedelta

from .models import Lead, LeadSource, LeadActivity, ConversionTracking, LeadNurturingCampaign
from .forms import (
    LeadForm, LeadActivityForm, ConversionForm, LeadFilterForm,
    LeadSourceForm, BulkLeadActionForm, LeadImportForm
)
from sales_funnel.models import SalesFunnel
from customers.models import Customer
from users.models import User


@login_required
def lead_dashboard(request):
    """Main lead generation dashboard"""
    
    # Get leads based on user role
    if request.user.role == 'salesperson':
        leads = Lead.objects.filter(assigned_to=request.user, is_active=True)
    elif request.user.role in ['supervisor', 'asm', 'avp']:
        # Get leads from team members
        team_members = User.objects.filter(
            team_membership__group__in=request.user.managed_groups.all(),
            role='salesperson'
        )
        leads = Lead.objects.filter(assigned_to__in=team_members, is_active=True)
    else:
        # Admins and executives see all leads
        leads = Lead.objects.filter(is_active=True)
    
    # Calculate dashboard statistics
    total_leads = leads.count()
    new_leads = leads.filter(status='new').count()
    qualified_leads = leads.filter(is_qualified=True).count()
    hot_leads = leads.filter(priority='hot').count()
    
    # Conversion statistics
    converted_leads = leads.filter(status='converted').count()
    conversion_rate = (converted_leads / total_leads * 100) if total_leads > 0 else 0
    
    # Recent activity
    recent_activities = LeadActivity.objects.filter(
        lead__in=leads,
        created_at__gte=timezone.now() - timedelta(days=7)
    ).order_by('-created_at')[:10]
    
    # Leads requiring follow-up
    follow_up_leads = leads.filter(
        next_follow_up_date__lte=timezone.now(),
        status__in=['contacted', 'qualified', 'proposal_sent']
    ).order_by('next_follow_up_date')[:5]
    
    # Top performing sources
    source_stats = LeadSource.objects.annotate(
        lead_count=Count('leads'),
        conversion_count=Count('leads', filter=Q(leads__status='converted'))
    ).filter(lead_count__gt=0).order_by('-conversion_count')[:5]
    
    context = {
        'total_leads': total_leads,
        'new_leads': new_leads,
        'qualified_leads': qualified_leads,
        'hot_leads': hot_leads,
        'converted_leads': converted_leads,
        'conversion_rate': conversion_rate,
        'recent_activities': recent_activities,
        'follow_up_leads': follow_up_leads,
        'source_stats': source_stats,
    }
    
    return render(request, 'lead_generation/dashboard.html', context)


@login_required
def lead_list(request):
    """List all leads with filtering and pagination"""
    
    # Get base queryset based on user role
    if request.user.role == 'salesperson':
        leads = Lead.objects.filter(assigned_to=request.user, is_active=True)
    elif request.user.role in ['supervisor', 'asm', 'avp']:
        team_members = User.objects.filter(
            team_membership__group__in=request.user.managed_groups.all(),
            role='salesperson'
        )
        leads = Lead.objects.filter(assigned_to__in=team_members, is_active=True)
    else:
        leads = Lead.objects.filter(is_active=True)
    
    # Apply filters
    filter_form = LeadFilterForm(request.GET, user=request.user)
    if filter_form.is_valid():
        if filter_form.cleaned_data.get('status'):
            leads = leads.filter(status=filter_form.cleaned_data['status'])
        if filter_form.cleaned_data.get('priority'):
            leads = leads.filter(priority=filter_form.cleaned_data['priority'])
        if filter_form.cleaned_data.get('source'):
            leads = leads.filter(source=filter_form.cleaned_data['source'])
        if filter_form.cleaned_data.get('assigned_to'):
            leads = leads.filter(assigned_to=filter_form.cleaned_data['assigned_to'])
        if filter_form.cleaned_data.get('score_min'):
            leads = leads.filter(lead_score__gte=filter_form.cleaned_data['score_min'])
        if filter_form.cleaned_data.get('score_max'):
            leads = leads.filter(lead_score__lte=filter_form.cleaned_data['score_max'])
        if filter_form.cleaned_data.get('created_from'):
            leads = leads.filter(created_at__date__gte=filter_form.cleaned_data['created_from'])
        if filter_form.cleaned_data.get('created_to'):
            leads = leads.filter(created_at__date__lte=filter_form.cleaned_data['created_to'])
    
    # Apply search
    search_query = request.GET.get('search', '')
    if search_query:
        leads = leads.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(company_name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(phone_number__icontains=search_query)
        )
    
    # Order leads by priority and score
    leads = leads.select_related('source', 'assigned_to').order_by(
        '-priority', '-lead_score', '-created_at'
    )
    
    # Pagination
    paginator = Paginator(leads, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'leads': page_obj,
        'filter_form': filter_form,
        'search_query': search_query,
        'total_count': leads.count(),
    }
    
    return render(request, 'lead_generation/lead_list.html', context)


@login_required
def lead_create(request):
    """Create a new lead"""
    
    if request.method == 'POST':
        form = LeadForm(request.POST, user=request.user)
        if form.is_valid():
            lead = form.save(commit=False)
            
            # Auto-assign to current user if they're a salesperson
            if request.user.role == 'salesperson' and not lead.assigned_to:
                lead.assigned_to = request.user
            
            lead.save()
            
            # Calculate initial lead score
            lead.calculate_lead_score()
            
            # Log creation activity
            LeadActivity.objects.create(
                lead=lead,
                activity_type='note',
                title='Lead Created',
                description=f'New lead created from {lead.source.name}',
                performed_by=request.user,
                outcome='successful'
            )
            
            messages.success(request, f'Lead "{lead.full_name}" created successfully!')
            return redirect('lead_generation:lead_detail', lead_id=lead.id)
    else:
        form = LeadForm(user=request.user)
    
    return render(request, 'lead_generation/lead_form.html', {
        'form': form,
        'title': 'Create New Lead'
    })


@login_required
def lead_detail(request, lead_id):
    """View lead details with activities and conversion options"""
    
    lead = get_object_or_404(Lead, id=lead_id)
    
    # Check permissions
    if request.user.role == 'salesperson' and lead.assigned_to != request.user:
        messages.error(request, 'You can only view leads assigned to you.')
        return redirect('lead_generation:lead_list')
    elif request.user.role in ['supervisor', 'asm', 'avp']:
        # Check if lead is assigned to team member
        team_members = User.objects.filter(
            team_membership__group__in=request.user.managed_groups.all(),
            role='salesperson'
        )
        if lead.assigned_to not in team_members:
            messages.error(request, 'You can only view leads from your team.')
            return redirect('lead_generation:lead_list')
    
    # Get recent activities
    activities = lead.activities.select_related('performed_by').order_by('-created_at')
    
    # Forms for quick actions
    activity_form = LeadActivityForm()
    conversion_form = ConversionForm()
    
    context = {
        'lead': lead,
        'activities': activities,
        'activity_form': activity_form,
        'conversion_form': conversion_form,
        'can_edit': request.user.role in ['admin', 'executive'] or lead.assigned_to == request.user,
        'can_convert': lead.status in ['qualified', 'proposal_sent', 'negotiating'] and not lead.converted_to_customer,
    }
    
    return render(request, 'lead_generation/lead_detail.html', context)


@login_required
def my_leads(request):
    """Show leads assigned to current salesperson"""
    
    if request.user.role != 'salesperson':
        return redirect('lead_generation:lead_list')
    
    leads = Lead.objects.filter(
        assigned_to=request.user,
        is_active=True
    ).select_related('source').order_by('-priority', '-lead_score', '-created_at')
    
    # Statistics for current salesperson
    total_leads = leads.count()
    qualified_leads = leads.filter(is_qualified=True).count()
    converted_leads = leads.filter(status='converted').count()
    conversion_rate = (converted_leads / total_leads * 100) if total_leads > 0 else 0
    
    context = {
        'leads': leads,
        'total_leads': total_leads,
        'qualified_leads': qualified_leads,
        'converted_leads': converted_leads,
        'conversion_rate': conversion_rate,
    }
    
    return render(request, 'lead_generation/my_leads.html', context)


@login_required
def lead_edit(request, lead_id):
    """Edit an existing lead"""
    
    lead = get_object_or_404(Lead, id=lead_id)
    
    # Check permissions
    if request.user.role == 'salesperson' and lead.assigned_to != request.user:
        messages.error(request, 'You can only edit leads assigned to you.')
        return redirect('lead_generation:lead_list')
    
    if request.method == 'POST':
        form = LeadForm(request.POST, instance=lead, user=request.user)
        if form.is_valid():
            updated_lead = form.save()
            
            # Recalculate lead score
            updated_lead.calculate_lead_score()
            
            messages.success(request, f'Lead "{updated_lead.full_name}" updated successfully!')
            return redirect('lead_generation:lead_detail', lead_id=updated_lead.id)
    else:
        form = LeadForm(instance=lead, user=request.user)
    
    return render(request, 'lead_generation/lead_form.html', {
        'form': form,
        'lead': lead,
        'title': f'Edit Lead: {lead.full_name}'
    })


@login_required
def convert_lead(request, lead_id):
    """Convert lead to customer"""
    
    lead = get_object_or_404(Lead, id=lead_id)
    
    # Check permissions
    if request.user.role == 'salesperson' and lead.assigned_to != request.user:
        messages.error(request, 'You can only convert leads assigned to you.')
        return redirect('lead_generation:lead_detail', lead_id=lead.id)
    
    # Check if already converted
    if lead.converted_to_customer:
        messages.warning(request, 'This lead has already been converted to a customer.')
        return redirect('lead_generation:lead_detail', lead_id=lead.id)
    
    if request.method == 'POST':
        # Simple conversion for now
        customer = lead.convert_to_customer(request.user)
        
        messages.success(request, f'Lead successfully converted to customer: {customer.company_name}')
        return redirect('customer_list')
    
    return render(request, 'lead_generation/convert_lead.html', {
        'lead': lead
    })


@login_required
@require_http_methods(["POST"])
def add_lead_activity(request, lead_id):
    """Add activity to a lead (AJAX)"""
    
    lead = get_object_or_404(Lead, id=lead_id)
    
    # Check permissions
    if request.user.role == 'salesperson' and lead.assigned_to != request.user:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    form = LeadActivityForm(request.POST)
    if form.is_valid():
        activity = form.save(commit=False)
        activity.lead = lead
        activity.performed_by = request.user
        activity.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Activity logged successfully'
        })
    else:
        return JsonResponse({'error': 'Invalid form data', 'errors': form.errors}, status=400)


@login_required
def lead_sources(request):
    """Manage lead sources"""
    
    sources = LeadSource.objects.annotate(
        lead_count=Count('leads'),
        conversion_count=Count('leads', filter=Q(leads__status='converted'))
    ).order_by('name')
    
    return render(request, 'lead_generation/source_list.html', {
        'sources': sources
    })


@login_required
def lead_source_create(request):
    """Create new lead source"""
    
    # Only allow admins and executives to create sources
    if request.user.role not in ['admin', 'executive']:
        messages.error(request, 'Only administrators can create lead sources.')
        return redirect('lead_generation:lead_sources')
    
    if request.method == 'POST':
        form = LeadSourceForm(request.POST)
        if form.is_valid():
            source = form.save()
            messages.success(request, f'Lead source "{source.name}" created successfully!')
            return redirect('lead_generation:lead_sources')
    else:
        form = LeadSourceForm()
    
    return render(request, 'lead_generation/source_form.html', {
        'form': form,
        'title': 'Create Lead Source'
    })


@login_required
def analytics_dashboard(request):
    """Lead generation analytics and reporting"""
    
    context = {
        'page_title': 'Lead Analytics',
        'message': 'Analytics dashboard coming soon!'
    }
    
    return render(request, 'lead_generation/analytics.html', context)


@login_required
def hot_leads(request):
    """Show all hot leads for quick access"""
    
    # Get hot leads based on user role
    if request.user.role == 'salesperson':
        leads = Lead.objects.filter(
            assigned_to=request.user,
            is_active=True
        )
    elif request.user.role in ['supervisor', 'asm', 'avp']:
        team_members = User.objects.filter(
            team_membership__group__in=request.user.managed_groups.all(),
            role='salesperson'
        )
        leads = Lead.objects.filter(
            assigned_to__in=team_members,
            is_active=True
        )
    else:
        leads = Lead.objects.filter(is_active=True)
    
    # Filter for hot leads
    hot_leads = leads.filter(
        Q(priority='hot') | Q(lead_score__gte=80)
    ).select_related('source', 'assigned_to').order_by('-lead_score', '-created_at')
    
    context = {
        'hot_leads': hot_leads,
        'total_count': hot_leads.count()
    }
    
    return render(request, 'lead_generation/hot_leads.html', context)


@login_required
def update_lead_status(request, lead_id):
    """Quick status update for leads"""
    
    lead = get_object_or_404(Lead, id=lead_id)
    
    # Check permissions
    if request.user.role == 'salesperson' and lead.assigned_to != request.user:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    return JsonResponse({'success': True, 'message': 'Status updated'})


@login_required
def lead_export(request):
    """Export leads to CSV"""
    
    return HttpResponse('Export feature coming soon!', content_type='text/plain')
