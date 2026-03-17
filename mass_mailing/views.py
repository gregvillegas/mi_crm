import threading
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, HttpResponseForbidden
from django.template import Template, Context
from django.utils import timezone
from .models import Campaign, CampaignRecipient, OptOut
from .forms import CampaignForm, UnsubscribeForm
from customers.models import Customer

@login_required
def campaign_list(request):
    if request.user.role == 'salesperson':
        campaigns = Campaign.objects.filter(created_by=request.user).order_by('-created_at')
    else:
        campaigns = Campaign.objects.all().order_by('-created_at')
        
    return render(request, 'mass_mailing/campaign_list.html', {'campaigns': campaigns})

@login_required
def campaign_create(request):
    if request.method == 'POST':
        form = CampaignForm(request.POST, user=request.user)
        if form.is_valid():
            campaign = form.save(commit=False)
            campaign.created_by = request.user
            campaign.save()
            
            # Add recipients
            customers = form.cleaned_data['customers']
            opted_out_emails = set(OptOut.objects.values_list('email', flat=True))
            
            for customer in customers:
                if customer.email and customer.email not in opted_out_emails:
                    CampaignRecipient.objects.create(
                        campaign=campaign,
                        customer=customer,
                        email=customer.email
                    )
            
            campaign.update_counts()
            messages.success(request, f"Campaign '{campaign.name}' created with {campaign.total_recipients} valid recipients.")
            return redirect('mass_mailing:campaign_detail', pk=campaign.pk)
    else:
        form = CampaignForm(user=request.user)
        
    return render(request, 'mass_mailing/campaign_form.html', {'form': form})

@login_required
def campaign_detail(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk)
    if request.user.role == 'salesperson' and campaign.created_by != request.user:
        return HttpResponseForbidden("You are not allowed to view this campaign.")
        
    recipients = campaign.recipients.all()
    
    return render(request, 'mass_mailing/campaign_detail.html', {
        'campaign': campaign,
        'recipients': recipients
    })

@login_required
def campaign_edit(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk)
    
    if request.user.role == 'salesperson' and campaign.created_by != request.user:
        return HttpResponseForbidden("You are not allowed to edit this campaign.")
        
    if campaign.status not in ['draft', 'scheduled']:
        messages.error(request, "You can only edit campaigns that are in Draft or Scheduled status.")
        return redirect('mass_mailing:campaign_detail', pk=pk)
        
    if request.method == 'POST':
        form = CampaignForm(request.POST, instance=campaign, user=request.user)
        if form.is_valid():
            campaign = form.save()
            
            # Rebuild recipients if needed
            # For simplicity, we just clear and re-add them if it's a draft
            if campaign.status == 'draft':
                campaign.recipients.all().delete()
                customers = form.cleaned_data['customers']
                opted_out_emails = set(OptOut.objects.values_list('email', flat=True))
                
                for customer in customers:
                    if customer.email and customer.email not in opted_out_emails:
                        CampaignRecipient.objects.create(
                            campaign=campaign,
                            customer=customer,
                            email=customer.email
                        )
                campaign.update_counts()
                
            messages.success(request, f"Campaign '{campaign.name}' has been updated.")
            return redirect('mass_mailing:campaign_detail', pk=campaign.pk)
    else:
        # Pre-populate selected customers
        initial_customers = Customer.objects.filter(id__in=campaign.recipients.values_list('customer_id', flat=True))
        form = CampaignForm(instance=campaign, user=request.user, initial={'customers': initial_customers})
        
    return render(request, 'mass_mailing/campaign_form.html', {'form': form, 'campaign': campaign})

@login_required
def campaign_cancel(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk)
    
    if request.user.role == 'salesperson' and campaign.created_by != request.user:
        return HttpResponseForbidden("You are not allowed to cancel this campaign.")
        
    if campaign.status in ['completed', 'cancelled']:
        messages.error(request, "This campaign cannot be cancelled anymore.")
        return redirect('mass_mailing:campaign_detail', pk=pk)
        
    if request.method == 'POST':
        # If it was a draft, just delete it entirely to clean up DB
        if campaign.status == 'draft':
            campaign.delete()
            messages.success(request, "Draft campaign deleted successfully.")
            return redirect('mass_mailing:campaign_list')
            
        # Otherwise, mark as cancelled so the worker stops sending
        campaign.status = 'cancelled'
        campaign.save()
        messages.success(request, "Campaign has been cancelled. No further emails will be sent.")
        return redirect('mass_mailing:campaign_detail', pk=pk)
        
    return render(request, 'mass_mailing/campaign_cancel.html', {'campaign': campaign})

@login_required
def campaign_preview(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk)
    if request.user.role == 'salesperson' and campaign.created_by != request.user:
        return HttpResponseForbidden("You are not allowed to preview this campaign.")
        
    # Get a sample recipient to preview
    sample_recipient = campaign.recipients.first()
    
    context_dict = {}
    if sample_recipient:
        context_dict = {
            'contact_name': sample_recipient.customer.contact_person_name,
            'company_name': sample_recipient.customer.company_name,
        }
    else:
        context_dict = {
            'contact_name': 'John Doe',
            'company_name': 'Sample Company Inc.',
        }
        
    # Convert newlines to <br> tags if not already HTML
    import re
    body_content = campaign.body_html
    if not re.search(r'<[a-z][\s\S]*>', body_content, re.IGNORECASE):
        body_content = body_content.replace('\n', '<br>')
        
    template = Template(body_content)
    context = Context(context_dict)
    rendered_body = template.render(context)
    
    return render(request, 'mass_mailing/campaign_preview.html', {
        'campaign': campaign,
        'rendered_body': rendered_body
    })

@login_required
def campaign_send(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk)
    if request.user.role == 'salesperson' and campaign.created_by != request.user:
        return HttpResponseForbidden("You are not allowed to send this campaign.")
        
    if campaign.status != 'draft':
        messages.warning(request, "This campaign is already scheduled or sending.")
        return redirect('mass_mailing:campaign_detail', pk=pk)
        
    # Update status to scheduled
    campaign.status = 'scheduled'
    if not campaign.scheduled_for:
        campaign.scheduled_for = timezone.now()
    campaign.save()
    
    messages.success(request, "Campaign has been queued for sending. It will be processed in the background.")
    
    # In a real production environment, a Cron job or Celery worker would pick this up.
    # For demonstration/sandbox purposes, we will trigger a background thread to process it.
    from django.core.management import call_command
    def run_worker():
        try:
            call_command('process_mail_queue')
        except Exception as e:
            print(f"Background worker error: {e}")
            
    thread = threading.Thread(target=run_worker)
    thread.daemon = True
    thread.start()
    
    return redirect('mass_mailing:campaign_detail', pk=pk)

def unsubscribe(request, recipient_id):
    recipient = get_object_or_404(CampaignRecipient, id=recipient_id)
    
    if request.method == 'POST':
        form = UnsubscribeForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            reason = form.cleaned_data['reason']
            
            # Record opt-out
            OptOut.objects.get_or_create(
                email=email,
                defaults={'customer': recipient.customer, 'reason': reason}
            )
            
            # Update recipient status if not already sent
            if recipient.status == 'pending':
                recipient.status = 'opted_out'
                recipient.save()
                recipient.campaign.update_counts()
                
            return render(request, 'mass_mailing/unsubscribe_success.html', {'email': email})
    else:
        form = UnsubscribeForm(initial={'email': recipient.email})
        
    return render(request, 'mass_mailing/unsubscribe.html', {'form': form, 'recipient': recipient})
