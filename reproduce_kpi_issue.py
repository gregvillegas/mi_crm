
import os
import django
from django.utils import timezone
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm_project.settings')
django.setup()

from users.models import User
from sales_monitoring.models import SalesActivity, ActivityType

def reproduce_kpi_issue():
    print("Setting up test data...")
    
    username = f"test_sp_kpi_{timezone.now().timestamp()}"
    salesperson, _ = User.objects.get_or_create(username=username, email=f"{username}@example.com", role='salesperson')
    act_type, _ = ActivityType.objects.get_or_create(name="Test Activity KPI")
    
    today = timezone.now()
    
    # 1. Create an activity that is COMPLETED but has NO actual_end
    # This simulates what happens if created via QuickActivityForm or BulkUpdate without handling actual_end
    activity = SalesActivity(
        title="Quick Logged Completed Activity",
        activity_type=act_type,
        salesperson=salesperson,
        status='completed',
        scheduled_start=today,
        scheduled_end=today + timedelta(hours=1)
    )
    # Note: We are NOT setting actual_end
    activity.save()
    
    print(f"Created activity: {activity.title}")
    print(f"  Status: {activity.status}")
    print(f"  Actual End: {activity.actual_end}")
    
    # 2. Check Dashboard Logic
    avp_count = SalesActivity.objects.filter(
        salesperson=salesperson,
        status='completed',
        actual_end__date=today.date()
    ).count()
    
    print(f"\nAVP/Salesperson Dashboard 'Completed Today' Count: {avp_count}")
    
    if avp_count == 0:
        print("ISSUE REPRODUCED: Count is 0 because actual_end is None.")
    else:
        print("ISSUE NOT REPRODUCED: Count is correct.")

    # Clean up
    activity.delete()
    salesperson.delete()

if __name__ == "__main__":
    reproduce_kpi_issue()
