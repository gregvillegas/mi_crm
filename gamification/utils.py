import random
from django.utils import timezone
from .models import Mission, UserMissionProgress

def generate_daily_missions(user):
    """
    Ensures a user has 3 active daily missions for today.
    """
    today = timezone.now().date()
    
    # Check existing missions for today
    existing_count = UserMissionProgress.objects.filter(
        user=user, 
        date_assigned=today,
        mission__mission_type='daily'
    ).count()
    
    needed = 3 - existing_count
    
    if needed > 0:
        # Get available daily missions
        # Exclude ones already assigned today (though logic above handles count, let's be safe)
        assigned_ids = UserMissionProgress.objects.filter(
            user=user,
            date_assigned=today
        ).values_list('mission_id', flat=True)
        
        available_missions = list(Mission.objects.filter(
            is_active=True, 
            mission_type='daily'
        ).exclude(id__in=assigned_ids))
        
        if not available_missions:
            return # No missions defined in DB yet
            
        # Randomly select needed amount
        # If fewer available than needed, take all
        to_assign = random.sample(available_missions, min(len(available_missions), needed))
        
        for mission in to_assign:
            UserMissionProgress.objects.create(
                user=user,
                mission=mission,
                date_assigned=today
            )
