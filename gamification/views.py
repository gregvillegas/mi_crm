from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import HttpResponseForbidden
from django.contrib import messages
from .models import GamificationProfile, Badge, UserBadge, PointLog, Mission
from .forms import MissionForm

@login_required
def leaderboard_view(request):
    # Top 10 by total points (Salespeople only)
    top_users = GamificationProfile.objects.select_related('user').filter(user__role='salesperson').order_by('-total_points')[:10]
    
    # Current User Rank
    user_rank = None
    
    # Only calculate rank if the user is a salesperson
    if request.user.role == 'salesperson':
        user_points = request.user.gamification_profile.total_points
        # Count salespeople with more points
        better_scores = GamificationProfile.objects.filter(user__role='salesperson', total_points__gt=user_points).count()
        user_rank = better_scores + 1
    
    context = {
        'top_users': top_users,
        'user_rank': user_rank,
        'my_profile': request.user.gamification_profile
    }
    return render(request, 'gamification/leaderboard.html', context)

@login_required
def badge_list_view(request):
    all_badges = Badge.objects.all()
    my_badges = UserBadge.objects.filter(user=request.user).select_related('badge')
    earned_badge_ids = set(my_badges.values_list('badge_id', flat=True))
    
    context = {
        'all_badges': all_badges,
        'earned_badge_ids': earned_badge_ids
    }
    return render(request, 'gamification/badges.html', context)

def can_manage_missions(user):
    return user.is_authenticated and user.role in ['admin','president','gm','vp','avp']

@login_required
def mission_list_view(request):
    if not can_manage_missions(request.user):
        return HttpResponseForbidden("Not allowed")
    missions = Mission.objects.all().order_by('-is_active','title')
    return render(request, 'gamification/mission_list.html', {'missions': missions})

@login_required
def mission_create_view(request):
    if not can_manage_missions(request.user):
        return HttpResponseForbidden("Not allowed")
    if request.method == 'POST':
        form = MissionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Mission created.")
            return redirect('missions_list')
    else:
        form = MissionForm()
    return render(request, 'gamification/mission_form.html', {'form': form})

@login_required
def mission_edit_view(request, pk):
    if not can_manage_missions(request.user):
        return HttpResponseForbidden("Not allowed")
    mission = get_object_or_404(Mission, pk=pk)
    if request.method == 'POST':
        form = MissionForm(request.POST, instance=mission)
        if form.is_valid():
            form.save()
            messages.success(request, "Mission updated.")
            return redirect('missions_list')
    else:
        form = MissionForm(instance=mission)
    return render(request, 'gamification/mission_form.html', {'form': form, 'mission': mission})
