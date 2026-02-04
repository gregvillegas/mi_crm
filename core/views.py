# -----------------------------------------------------------------------------
# 5. core/views.py (for handling login, logout, and home page)
# -----------------------------------------------------------------------------
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.contrib import messages
from django.db.models import Sum, Count
from sales_funnel.models import SalesFunnel
from teams.models import Team, Group, TeamMembership

@login_required
def home(request):
    user = request.user
    context = {'user': user}
    
    # Add sales funnel data for eligible users
    if user.role in ['salesperson', 'supervisor', 'teamlead', 'asm', 'avp', 'admin', 'president', 'gm', 'vp']:
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
        
        # Calculate funnel statistics
        funnel_stats = {
            'quoted_count': funnel_entries.filter(stage='quoted').count(),
            'closable_count': funnel_entries.filter(stage='closable').count(),
            'project_count': funnel_entries.filter(stage='project').count(),
            'total_value': funnel_entries.aggregate(Sum('retail'))['retail__sum'] or 0,
            'total_entries': funnel_entries.count(),
        }
        
        # Get recent entries for quick view (limit to 5)
        recent_entries = funnel_entries.select_related('salesperson', 'customer').order_by('-date_created')[:5]
        
        context.update({
            'funnel_stats': funnel_stats,
            'recent_funnel_entries': recent_entries,
            'show_funnel': True,
            'can_add_funnel': user.role == 'salesperson',
        })
    
    return render(request, 'core/home.html', context)

def logout_view(request):
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    return redirect('login')

