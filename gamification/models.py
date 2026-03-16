from django.db import models
from django.conf import settings
from django.utils import timezone
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

class GamificationProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='gamification_profile')
    total_points = models.IntegerField(default=0)
    current_level = models.IntegerField(default=1)
    current_streak = models.IntegerField(default=0)
    last_activity_date = models.DateField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.user.username} - Level {self.current_level} ({self.total_points} pts)"
    
    def add_points(self, points):
        self.total_points += points
        # Level up logic: Level N requires N * 1000 points
        # Or simpler: Level = 1 + (points // 1000)
        self.current_level = 1 + (self.total_points // 1000)
        self.save()

class Badge(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    icon = models.CharField(max_length=50, help_text="FontAwesome class (e.g., 'fas fa-trophy')")
    point_reward = models.IntegerField(default=0)
    criteria_code = models.CharField(max_length=50, unique=True, help_text="Code used in signals to trigger badge check")
    
    def __str__(self):
        return self.name

class UserBadge(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='badges')
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE)
    date_awarded = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'badge')

class PointLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='point_logs')
    action_type = models.CharField(max_length=100)
    points_amount = models.IntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Generic relation to link to any object (Lead, Proposal, etc.)
    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    def __str__(self):
        return f"{self.user.username} - {self.action_type} (+{self.points_amount})"

class Mission(models.Model):
    MISSION_TYPES = (
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    mission_type = models.CharField(max_length=20, choices=MISSION_TYPES, default='daily')
    target_action = models.CharField(max_length=100, help_text="Action code (e.g., 'create_lead')")
    target_count = models.IntegerField(default=1)
    reward_points = models.IntegerField(default=50)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.title} ({self.get_mission_type_display()})"

class UserMissionProgress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='mission_progress')
    mission = models.ForeignKey(Mission, on_delete=models.CASCADE)
    current_count = models.IntegerField(default=0)
    is_completed = models.BooleanField(default=False)
    date_assigned = models.DateField(default=timezone.now)
    date_completed = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ('user', 'mission', 'date_assigned')
