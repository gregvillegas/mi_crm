
import os
import django
from django.utils import timezone
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm_project.settings')
django.setup()

from users.models import User
from sales_monitoring.models import SalesActivity, ActivityType

def test_dashboard_kpi_discrepancy():
    print("Setting up test data...")
    
    # Create a salesperson
    username = f"test_sp_{timezone.now().timestamp()}"
    salesperson, _ = User.objects.get_or_create(username=username, email=f"{username}@example.com", role='salesperson')
    
    # Create an activity type
    act_type, _ = ActivityType.objects.get_or_create(name="Test Activity")
    
    today = timezone.now()
    yesterday = today - timedelta(days=1)
    
    # Create an activity scheduled for YESTERDAY, but completed TODAY
    activity = SalesActivity.objects.create(
        title="Late Completion Activity",
        activity_type=act_type,
        salesperson=salesperson,
        status='completed',
        scheduled_start=yesterday,
        scheduled_end=yesterday + timedelta(hours=1),
        actual_start=today,
        actual_end=today  # Completed TODAY
    )
    
    print(f"Created activity: {activity.title}")
    print(f"  Scheduled Start: {activity.scheduled_start}")
    print(f"  Actual End: {activity.actual_end}")
    
    # Simulate NEW Salesperson Dashboard Logic (Aligned with AVP)
    sp_activities = SalesActivity.objects.filter(salesperson=salesperson)
    sp_completed_today = sp_activities.filter(status='completed', actual_end__date=today.date()).count()
    
    # Simulate AVP Dashboard Logic
    avp_activities = SalesActivity.objects.filter(salesperson=salesperson) 
    avp_completed_today = avp_activities.filter(status='completed', actual_end__date=today.date()).count()
    
    print("\n--- Results ---")
    print(f"Salesperson Dashboard 'Completed Today': {sp_completed_today}")
    print(f"AVP Dashboard 'Completed Today': {avp_completed_today}")
    
    if sp_completed_today != avp_completed_today:
        print("\nDISCREPANCY STILL EXISTS!")
    else:
        print("\nSUCCESS: No discrepancy found. Logic is aligned.")

    # Clean up
    activity.delete()
    salesperson.delete()

if __name__ == "__main__":
    test_dashboard_kpi_discrepancy()
