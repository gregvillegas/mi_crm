import requests
from django.conf import settings
from .models import Ticket

def create_redmine_ticket(ticket_obj):
    """
    Creates a new issue in Redmine based on a Ticket object.
    Returns the Redmine ID if successful, or raises an exception.
    """
    url = f"{settings.REDMINE_URL}/issues.json"
    headers = {
        'X-Redmine-API-Key': settings.REDMINE_API_KEY,
        'Content-Type': 'application/json'
    }
    
    # Map priority (Redmine typically uses 1-5, Low to Immediate)
    # Defaulting to 4 (Normal) based on Redmine API response
    priority_map = {
        'low': 3,
        'normal': 4,
        'high': 5,
        'urgent': 6,
        'immediate': 7
    }
    
    priority_id = priority_map.get(ticket_obj.priority.lower(), 4)

    data = {
        "issue": {
            "project_id": getattr(settings, 'REDMINE_PROJECT_ID', 14),
            "tracker_id": getattr(settings, 'REDMINE_TRACKER_ID', 7),
            "subject": f"[{ticket_obj.customer.company_name}] {ticket_obj.title}",
            "description": f"CRM Ticket #{ticket_obj.id}\nCustomer: {ticket_obj.customer.company_name}\nCreated By: {ticket_obj.created_by.get_full_name()}\n\n{ticket_obj.description}",
            "priority_id": priority_id,
        }
    }
    
    try:
        response = requests.post(url, json=data, headers=headers, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        issue_id = result['issue']['id']
        
        # Update local ticket
        ticket_obj.redmine_ticket_id = str(issue_id)
        ticket_obj.redmine_url = f"{settings.REDMINE_URL}/issues/{issue_id}"
        ticket_obj.save()
        
        return issue_id
        
    except requests.exceptions.RequestException as e:
        # Log the error or re-raise
        print(f"Error creating Redmine ticket: {e}")
        if hasattr(e, 'response') and e.response:
             print(f"Response content: {e.response.text}")
        raise e

def get_redmine_ticket_details(redmine_id):
    """
    Fetches the current details (status and assigned user) of a Redmine ticket.
    Returns a dictionary or None if failed.
    """
    if not redmine_id:
        return None
        
    url = f"{settings.REDMINE_URL}/issues/{redmine_id}.json"
    headers = {
        'X-Redmine-API-Key': settings.REDMINE_API_KEY,
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()
        
        result = response.json()
        issue = result.get('issue', {})
        
        details = {
            'status_name': issue.get('status', {}).get('name'),
            'assigned_to_name': issue.get('assigned_to', {}).get('name')
        }
        return details
        
    except Exception as e:
        print(f"Error fetching Redmine ticket details: {e}")
        return None

def get_full_redmine_ticket(redmine_id):
    """
    Fetches comprehensive details of a Redmine ticket including journals (comments).
    """
    if not redmine_id:
        return None
        
    url = f"{settings.REDMINE_URL}/issues/{redmine_id}.json?include=journals"
    headers = {
        'X-Redmine-API-Key': settings.REDMINE_API_KEY,
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        return result.get('issue', {})
        
    except Exception as e:
        print(f"Error fetching full Redmine ticket: {e}")
        return None
