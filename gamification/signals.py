from datetime import timedelta
from django.db.models.signals import post_save
from django.db.models import Q
from django.dispatch import receiver
from django.utils import timezone
from .models import GamificationProfile, PointLog, Badge, UserBadge, Mission, UserMissionProgress
from lead_generation.models import Lead
from sales_proposals.models import Proposal
from sales_funnel.models import SalesFunnel
from users.models import User
import logging

logger = logging.getLogger(__name__)

# --- Helper Functions ---

def award_points(user, action_type, points, related_object=None):
    """
    Award points to a user and log the action.
    Also updates mission progress if applicable.
    """
    if not user:
        return

    profile, created = GamificationProfile.objects.get_or_create(user=user)
    
    # Check if we already awarded points for this object (prevent duplicates)
    if related_object:
        content_type = related_object._meta.model_name
        object_id = related_object.pk
        # You might want a stricter check here, but for now we assume distinct events
        # E.g. one point log per action per object
    
    # Update Profile
    profile.add_points(points)
    
    # Update Streak (Simple logic: if last activity was yesterday, increment. If today, do nothing. Else reset)
    today = timezone.now().date()
    if profile.last_activity_date:
        delta = today - profile.last_activity_date
        if delta.days == 1:
            profile.current_streak += 1
        elif delta.days > 1:
            profile.current_streak = 1 # Reset
    else:
        profile.current_streak = 1
        
    profile.last_activity_date = today
    profile.save()
    
    # Log Points
    PointLog.objects.create(
        user=user,
        action_type=action_type,
        points_amount=points,
        content_object=related_object
    )
    
    # Check Missions
    check_missions(user, action_type)
    
    # Check Badges
    check_badges(user, profile)

def check_missions(user, action_type):
    """
    Update progress for active missions matching the action type.
    """
    today = timezone.now().date()
    week_start = today - timedelta(days=today.weekday())
    progress_entries = UserMissionProgress.objects.filter(
        user=user,
        mission__target_action=action_type,
        is_completed=False
    ).filter(
        Q(mission__mission_type='daily', date_assigned=today) |
        Q(mission__mission_type='weekly', date_assigned=week_start)
    )
    
    for entry in progress_entries:
        entry.current_count += 1
        if entry.current_count >= entry.mission.target_count:
            entry.is_completed = True
            entry.date_completed = timezone.now()
            # Award Mission Bonus
            award_points(user, f"Mission Complete: {entry.mission.title}", entry.mission.reward_points)
        entry.save()

def check_badges(user, profile):
    """
    Check if user qualifies for any new badges.
    """
    # 1. Point Milestones
    if profile.total_points >= 1000:
        award_badge(user, 'score_1000')
    if profile.total_points >= 5000:
        award_badge(user, 'score_5000')
        
    # 2. Streak Milestones
    if profile.current_streak >= 7:
        award_badge(user, 'streak_7')
    if profile.current_streak >= 30:
        award_badge(user, 'streak_30')

def award_badge(user, criteria_code):
    try:
        badge = Badge.objects.get(criteria_code=criteria_code)
        if not UserBadge.objects.filter(user=user, badge=badge).exists():
            UserBadge.objects.create(user=user, badge=badge)
            # Optional: Award bonus points for badge?
            if badge.point_reward > 0:
                award_points(user, f"Badge Earned: {badge.name}", badge.point_reward)
    except Badge.DoesNotExist:
        pass

# --- Signals ---

@receiver(post_save, sender=Lead)
def lead_created(sender, instance, created, **kwargs):
    if created and instance.created_by:
        award_points(instance.created_by, 'create_lead', 5, instance)

@receiver(post_save, sender=Proposal)
def proposal_created(sender, instance, created, **kwargs):
    if created and instance.created_by:
        award_points(instance.created_by, 'create_proposal', 10, instance)
    elif instance.status == 'sent': 
        # You might want to track status changes specifically
        # But for now let's stick to creation or maybe a custom signal call
        pass

@receiver(post_save, sender=SalesFunnel)
def deal_closed(sender, instance, created, **kwargs):
    # Check if deal is won/closed
    if instance.deal_outcome == 'won' and instance.salesperson:
        # Determine points based on value
        points = 50
        if instance.retail >= 1000000: # 1 Million
            points = 100
            award_badge(instance.salesperson, 'millionaire_deal')
            
        # We need to ensure we don't award points multiple times for the same deal update
        # This simple check might not be enough if status flips back and forth
        # A more robust way is to check if we already awarded 'deal_won' points for this object
        if not PointLog.objects.filter(
            user=instance.salesperson, 
            action_type='deal_won', 
            object_id=instance.pk, 
            content_type__model='salesfunnel'
        ).exists():
            award_points(instance.salesperson, 'deal_won', points, instance)

from django.contrib.auth.signals import user_logged_in
from .utils import generate_daily_missions, generate_weekly_missions

@receiver(user_logged_in)
def user_login_reward(sender, request, user, **kwargs):
    # Award point for daily login (once per day)
    today = timezone.now().date()
    # Check if we already logged a login point for today
    if not PointLog.objects.filter(
        user=user, 
        action_type='daily_login', 
        timestamp__date=today
    ).exists():
        award_points(user, 'daily_login', 1)
        
    # Generate missions for today
    generate_daily_missions(user)
    generate_weekly_missions(user)
