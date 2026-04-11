import threading
import os
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.utils import timezone
from django.db.models import Max
from django.core.files.base import ContentFile
from .models import Campaign, CampaignRecipient, OptOut, MediaLibraryAsset, CampaignAsset
from .forms import CampaignForm, UnsubscribeForm, CampaignAssetFormSet, MediaLibraryAssetForm
from .rendering import render_campaign_html
from customers.models import Customer


def can_manage_media_library(user):
    return user.role in ['admin', 'marketing']


def can_view_media_library(user):
    return user.role in ['admin', 'marketing']


def sync_selected_library_assets(campaign, selected_ids, user):
    selected_ids = {int(i) for i in selected_ids if str(i).isdigit()}
    existing = {asset.library_asset_id: asset for asset in campaign.assets.filter(library_asset__isnull=False)}

    # Delete deselected library-based assets
    for library_id, asset in list(existing.items()):
        if library_id not in selected_ids:
            asset.delete()

    # Add newly selected library assets
    max_sort = campaign.assets.aggregate(max_sort=Max('sort_order'))['max_sort'] or 0
    new_library_ids = [library_id for library_id in selected_ids if library_id not in existing]
    for offset, library_asset in enumerate(MediaLibraryAsset.objects.filter(id__in=new_library_ids, is_active=True), start=1):
        library_asset.file.open('rb')
        content = library_asset.file.read()
        library_asset.file.close()
        filename = os.path.basename(library_asset.file.name)
        campaign_asset = CampaignAsset(
            campaign=campaign,
            library_asset=library_asset,
            display_name=library_asset.title,
            embed_inline=True,
            sort_order=max_sort + offset,
            uploaded_by=user,
        )
        campaign_asset.file.save(filename, ContentFile(content), save=True)

def get_allowed_campaigns(user):
    """Returns a queryset of campaigns the user is allowed to see based on their role."""
    if user.role == 'salesperson':
        return Campaign.objects.filter(created_by=user)
        
    elif user.role == 'supervisor':
        member_ids = [user.id]
        for group in user.managed_groups.all():
            member_ids.extend(group.members.values_list('user_id', flat=True))
        return Campaign.objects.filter(created_by_id__in=member_ids)
        
    elif user.role == 'teamlead':
        member_ids = [user.id]
        for group in user.led_groups.all():
            member_ids.extend(group.members.values_list('user_id', flat=True))
        return Campaign.objects.filter(created_by_id__in=member_ids)
        
    elif user.role == 'asm':
        member_ids = [user.id]
        for team in user.asm_teams.all():
            for group in team.groups.all():
                member_ids.extend(group.members.values_list('user_id', flat=True))
                if group.supervisor:
                    member_ids.append(group.supervisor.id)
        return Campaign.objects.filter(created_by_id__in=member_ids)
        
    elif user.role == 'avp':
        member_ids = [user.id]
        for team in user.managed_teams.all():
            for group in team.groups.all():
                member_ids.extend(group.members.values_list('user_id', flat=True))
                if group.supervisor:
                    member_ids.append(group.supervisor.id)
        return Campaign.objects.filter(created_by_id__in=member_ids)
        
    else:
        # Admins, Presidents, VPs, GMs can see all
        return Campaign.objects.all()

@login_required
def campaign_list(request):
    campaigns = get_allowed_campaigns(request.user).order_by('-created_at')
    return render(request, 'mass_mailing/campaign_list.html', {'campaigns': campaigns})


@login_required
def media_library(request):
    if not can_view_media_library(request.user):
        messages.error(request, "You don't have permission to access the Media Library.")
        return redirect('mass_mailing:campaign_list')

    assets = MediaLibraryAsset.objects.all().order_by('-created_at')
    library_form = MediaLibraryAssetForm()

    if request.method == 'POST':
        if 'upload_library_media' in request.POST:
            if not can_manage_media_library(request.user):
                messages.error(request, "You don't have permission to upload media.")
                return redirect('mass_mailing:media_library')
            library_form = MediaLibraryAssetForm(request.POST, request.FILES)
            if library_form.is_valid():
                media = library_form.save(commit=False)
                media.uploaded_by = request.user
                media.save()
                messages.success(request, f'Media "{media.title}" uploaded successfully.')
                return redirect('mass_mailing:media_library')

        elif 'delete_media' in request.POST:
            if not can_manage_media_library(request.user):
                messages.error(request, "You don't have permission to delete media.")
                return redirect('mass_mailing:media_library')
            asset = get_object_or_404(MediaLibraryAsset, pk=request.POST.get('asset_id'))
            asset.delete()
            messages.success(request, "Media deleted from the library.")
            return redirect('mass_mailing:media_library')

        elif 'toggle_media_status' in request.POST:
            if not can_manage_media_library(request.user):
                messages.error(request, "You don't have permission to update media.")
                return redirect('mass_mailing:media_library')
            asset = get_object_or_404(MediaLibraryAsset, pk=request.POST.get('asset_id'))
            asset.is_active = not asset.is_active
            asset.save(update_fields=['is_active'])
            messages.success(request, f'"{asset.title}" is now {"active" if asset.is_active else "inactive"}.')
            return redirect('mass_mailing:media_library')

    return render(request, 'mass_mailing/media_library.html', {
        'assets': assets,
        'library_form': library_form,
        'can_manage_media_library': can_manage_media_library(request.user),
        'can_view_media_library': can_view_media_library(request.user),
    })

@login_required
def campaign_create(request):
    library_assets = MediaLibraryAsset.objects.filter(is_active=True)
    selected_library_ids = []
    if request.method == 'POST':
        if 'upload_library_media' in request.POST and can_manage_media_library(request.user):
            library_form = MediaLibraryAssetForm(request.POST, request.FILES)
            form = CampaignForm(user=request.user)
            asset_formset = CampaignAssetFormSet(prefix='assets')
            if library_form.is_valid():
                media = library_form.save(commit=False)
                media.uploaded_by = request.user
                media.save()
                messages.success(request, f'Media "{media.title}" uploaded to the library.')
                return redirect('mass_mailing:campaign_create')
            return render(request, 'mass_mailing/campaign_form.html', {
                'form': form,
                'asset_formset': asset_formset,
                'library_form': library_form,
                'library_assets': library_assets,
                'selected_library_ids': selected_library_ids,
                'can_manage_media_library': can_manage_media_library(request.user),
                'can_view_media_library': can_view_media_library(request.user),
            })
        form = CampaignForm(request.POST, user=request.user)
        asset_formset = CampaignAssetFormSet(request.POST, request.FILES, prefix='assets')
        selected_library_ids = request.POST.getlist('library_assets')
        if form.is_valid() and asset_formset.is_valid():
            campaign = form.save(commit=False)
            campaign.created_by = request.user
            campaign.save()
            asset_formset.instance = campaign
            assets = asset_formset.save(commit=False)
            for asset in assets:
                asset.campaign = campaign
                asset.uploaded_by = request.user
                asset.save()
            for obj in asset_formset.deleted_objects:
                obj.delete()
            sync_selected_library_assets(campaign, selected_library_ids, request.user)
            
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
        asset_formset = CampaignAssetFormSet(prefix='assets')
        library_form = MediaLibraryAssetForm()
        
    if request.method != 'POST' or 'upload_library_media' not in request.POST:
        library_form = locals().get('library_form', MediaLibraryAssetForm())

    return render(request, 'mass_mailing/campaign_form.html', {
        'form': form,
        'asset_formset': asset_formset,
        'library_form': library_form,
        'library_assets': library_assets,
        'selected_library_ids': selected_library_ids,
        'can_manage_media_library': can_manage_media_library(request.user),
        'can_view_media_library': can_view_media_library(request.user),
    })

@login_required
def campaign_detail(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk)
    
    if not get_allowed_campaigns(request.user).filter(pk=pk).exists():
        return HttpResponseForbidden("You are not allowed to view this campaign.")
        
    recipients = campaign.recipients.all()
    
    return render(request, 'mass_mailing/campaign_detail.html', {
        'campaign': campaign,
        'recipients': recipients
    })

@login_required
def campaign_edit(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk)
    library_assets = MediaLibraryAsset.objects.filter(is_active=True)
    selected_library_ids = list(campaign.assets.filter(library_asset__isnull=False).values_list('library_asset_id', flat=True))
    
    if not get_allowed_campaigns(request.user).filter(pk=pk).exists():
        return HttpResponseForbidden("You are not allowed to edit this campaign.")
        
    if campaign.status not in ['draft', 'scheduled']:
        messages.error(request, "You can only edit campaigns that are in Draft or Scheduled status.")
        return redirect('mass_mailing:campaign_detail', pk=pk)
        
    if request.method == 'POST':
        if 'upload_library_media' in request.POST and can_manage_media_library(request.user):
            library_form = MediaLibraryAssetForm(request.POST, request.FILES)
            initial_customers = Customer.objects.filter(id__in=campaign.recipients.values_list('customer_id', flat=True))
            form = CampaignForm(instance=campaign, user=request.user, initial={'customers': initial_customers})
            asset_formset = CampaignAssetFormSet(instance=campaign, prefix='assets')
            if library_form.is_valid():
                media = library_form.save(commit=False)
                media.uploaded_by = request.user
                media.save()
                messages.success(request, f'Media "{media.title}" uploaded to the library.')
                return redirect('mass_mailing:campaign_edit', pk=campaign.pk)
            return render(request, 'mass_mailing/campaign_form.html', {
                'form': form,
                'campaign': campaign,
                'asset_formset': asset_formset,
                'library_form': library_form,
                'library_assets': library_assets,
                'selected_library_ids': selected_library_ids,
                'can_manage_media_library': can_manage_media_library(request.user),
                'can_view_media_library': can_view_media_library(request.user),
            })
        form = CampaignForm(request.POST, instance=campaign, user=request.user)
        asset_formset = CampaignAssetFormSet(request.POST, request.FILES, instance=campaign, prefix='assets')
        selected_library_ids = request.POST.getlist('library_assets')
        if form.is_valid() and asset_formset.is_valid():
            campaign = form.save()
            assets = asset_formset.save(commit=False)
            for asset in assets:
                asset.campaign = campaign
                if not asset.uploaded_by_id:
                    asset.uploaded_by = request.user
                asset.save()
            for obj in asset_formset.deleted_objects:
                obj.delete()
            sync_selected_library_assets(campaign, selected_library_ids, request.user)
            
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
        asset_formset = CampaignAssetFormSet(instance=campaign, prefix='assets')
        library_form = MediaLibraryAssetForm()
        
    if request.method != 'POST' or 'upload_library_media' not in request.POST:
        library_form = locals().get('library_form', MediaLibraryAssetForm())

    return render(request, 'mass_mailing/campaign_form.html', {
        'form': form,
        'campaign': campaign,
        'asset_formset': asset_formset,
        'library_form': library_form,
        'library_assets': library_assets,
        'selected_library_ids': selected_library_ids,
        'can_manage_media_library': can_manage_media_library(request.user),
        'can_view_media_library': can_view_media_library(request.user),
    })

@login_required
def campaign_cancel(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk)
    
    if not get_allowed_campaigns(request.user).filter(pk=pk).exists():
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
    
    if not get_allowed_campaigns(request.user).filter(pk=pk).exists():
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
        
    rendered_body = render_campaign_html(campaign, context_dict, preview=True)
    
    return render(request, 'mass_mailing/campaign_preview.html', {
        'campaign': campaign,
        'rendered_body': rendered_body
    })

@login_required
def campaign_send(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk)
    
    if not get_allowed_campaigns(request.user).filter(pk=pk).exists():
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
    
    # If the campaign is scheduled for the future, we need to wait.
    # In a proper setup, a cron job runs every minute to check this.
    # Here, we'll spawn a thread that waits until the scheduled time.
    def run_worker():
        try:
            campaign.refresh_from_db()
            if campaign.status == 'cancelled':
                return
                
            # Calculate how long to wait
            now = timezone.now()
            if campaign.scheduled_for and campaign.scheduled_for > now:
                wait_seconds = (campaign.scheduled_for - now).total_seconds()
                if wait_seconds > 0:
                    import time
                    time.sleep(wait_seconds)
            
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
