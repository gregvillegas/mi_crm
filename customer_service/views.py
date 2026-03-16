from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Ticket
from customers.models import Customer
from users.models import User
from .redmine_utils import create_redmine_ticket, get_redmine_ticket_details, get_full_redmine_ticket

@login_required
def create_ticket_for_customer(request, customer_id):
    customer = get_object_or_404(Customer, id=customer_id)
    
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        priority = request.POST.get('priority', 'normal')
        create_redmine = request.POST.get('create_redmine') == 'on'
        
        ticket = Ticket.objects.create(
            customer=customer,
            title=title,
            description=description,
            priority=priority,
            created_by=request.user,
            status='new'
        )
        
        if create_redmine:
            try:
                # Call Redmine API
                issue_id = create_redmine_ticket(ticket)
                messages.success(request, f"Ticket #{ticket.id} created and synced to Redmine (Issue #{issue_id}).")
            except Exception as e:
                # In case of failure, we still keep the local ticket but warn the user
                messages.warning(request, f"Ticket created locally but Redmine sync failed: {str(e)}")
        else:
            messages.success(request, f"Ticket #{ticket.id} created locally.")
            
        return redirect('customer_detail', pk=customer.id)

@login_required
def sync_ticket_status(request, ticket_id):
    """
    Manually sync the status and assigned user of a specific ticket from Redmine.
    """
    ticket = get_object_or_404(Ticket, id=ticket_id)
    
    if not ticket.redmine_ticket_id:
        messages.warning(request, "This ticket is not linked to Redmine.")
        return redirect('customer_detail', pk=ticket.customer.id)
        
    details = get_redmine_ticket_details(ticket.redmine_ticket_id)
    
    if details:
        status_name = details.get('status_name')
        assigned_to_name = details.get('assigned_to_name')
        
        updates = []
        
        if status_name:
            ticket.status = status_name.lower() # basic mapping attempt
            updates.append(f"Status: {status_name}")
            
        if assigned_to_name:
            # Try to find a local user with a matching name
            # Redmine returns full name (e.g., "Greg Villegas")
            # We will search by first_name and last_name, or just try to match
            try:
                parts = assigned_to_name.split(' ', 1)
                if len(parts) == 2:
                    first_name, last_name = parts
                    user = User.objects.filter(first_name__iexact=first_name, last_name__iexact=last_name).first()
                else:
                    user = User.objects.filter(username__iexact=assigned_to_name).first()
                    
                if user:
                    ticket.assigned_to = user
                    updates.append(f"Assigned To: {user.get_full_name()}")
                else:
                    updates.append(f"Assigned To: {assigned_to_name} (Not found in CRM)")
            except Exception as e:
                print(f"Error matching assigned user: {e}")
                
        ticket.save()
        
        if updates:
            messages.success(request, f"Ticket synced. Updates: {', '.join(updates)}")
        else:
            messages.info(request, "Ticket synced. No changes detected.")
    else:
        messages.error(request, "Failed to fetch details from Redmine.")
        
    return redirect('customer_detail', pk=ticket.customer.id)

@login_required
def ticket_detail(request, ticket_id):
    """
    Displays the details of a ticket, pulling live data (including comments/journals)
    from Redmine so the user doesn't need to log into Redmine.
    """
    ticket = get_object_or_404(Ticket, id=ticket_id)
    
    # Check authorization: 
    # Only allow if user is the salesperson of the customer, the creator of the ticket, 
    # or an admin/manager.
    user = request.user
    if user.role == 'salesperson' and ticket.customer.salesperson != user and ticket.created_by != user:
        messages.error(request, "You do not have permission to view this ticket.")
        return redirect('customer_detail', pk=ticket.customer.id)
        
    redmine_data = None
    if ticket.redmine_ticket_id:
        redmine_data = get_full_redmine_ticket(ticket.redmine_ticket_id)
        
    context = {
        'ticket': ticket,
        'redmine_data': redmine_data
    }
    
    return render(request, 'customer_service/ticket_detail.html', context)
