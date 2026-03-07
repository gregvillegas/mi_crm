
import os
import django
from django.db.models import Q

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm_project.settings')
django.setup()

from sales_monitoring.models import SalesActivity, ActivityLog

def fix_missing_actual_end():
    print("Finding completed activities with missing actual_end...")
    
    activities = SalesActivity.objects.filter(
        status='completed',
        actual_end__isnull=True
    )
    
    count = activities.count()
    print(f"Found {count} activities to fix.")
    
    updated_count = 0
    
    for activity in activities:
        # Try to find when it was completed from logs
        completion_log = ActivityLog.objects.filter(
            activity=activity,
            action__in=['completed', 'status_changed']
        ).order_by('-timestamp').first()
        
        completion_time = None
        
        if completion_log:
            # Check if status changed to completed
            if completion_log.action == 'status_changed':
                new_val = completion_log.new_value or {}
                if new_val.get('status') == 'completed':
                    completion_time = completion_log.timestamp
            elif completion_log.action == 'completed':
                completion_time = completion_log.timestamp
        
        # If no log found or log didn't confirm completion time, use created_at if created as completed
        if not completion_time:
            # Fallback to updated_at or created_at
            # If we use updated_at, it might be recent. 
            # If created_at is close to scheduled_start, maybe it was created as completed.
            print(f"  No completion log for '{activity.title}' (ID: {activity.id}). Using created_at.")
            completion_time = activity.created_at
            
        print(f"  Fixing '{activity.title}' (ID: {activity.id}): Setting actual_end to {completion_time}")
        
        activity.actual_end = completion_time
        # We also need to set actual_start if missing
        if not activity.actual_start:
            activity.actual_start = activity.scheduled_start if activity.scheduled_start else completion_time
            
        # Use update() to avoid triggering save() which might reset to now() or update updated_at
        SalesActivity.objects.filter(id=activity.id).update(
            actual_end=activity.actual_end,
            actual_start=activity.actual_start
        )
        updated_count += 1
        
    print(f"Successfully fixed {updated_count} activities.")

if __name__ == "__main__":
    fix_missing_actual_end()
