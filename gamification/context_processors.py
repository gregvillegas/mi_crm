from .models import GamificationProfile

def gamification_status(request):
    """
    Makes the user's gamification profile available in all templates.
    """
    if request.user.is_authenticated:
        try:
            profile = request.user.gamification_profile
            return {
                'user_points': profile.total_points,
                'user_level': profile.current_level,
                'user_streak': profile.current_streak
            }
        except GamificationProfile.DoesNotExist:
            return {
                'user_points': 0,
                'user_level': 1,
                'user_streak': 0
            }
    return {}
