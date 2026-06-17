import time
from email.mime.image import MIMEImage
from django.core.management.base import BaseCommand
from django.core.mail import EmailMultiAlternatives, get_connection
from django.utils import timezone
from django.urls import reverse
from django.conf import settings
from mass_mailing.models import Campaign, OptOut
from mass_mailing.rendering import render_campaign_html
from sales_monitoring.models import SalesActivity, ActivityType, EmailActivity
from gamification.models import PointLog, GamificationProfile

def insert_before_body_close(html_content, insert_html):
    html_content = html_content or ''
    insert_html = insert_html or ''
    lower = html_content.lower()
    for close_tag in ('</body>', '</html>'):
        idx = lower.rfind(close_tag)
        if idx != -1:
            return html_content[:idx] + insert_html + html_content[idx:]
    return html_content + insert_html

class Command(BaseCommand):
    help = 'Process the email queue for scheduled mass mailing campaigns'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=50, help='Maximum number of emails to send per run')
        parser.add_argument('--delay', type=int, default=1, help='Delay in seconds between emails to avoid spam filters')

    def handle(self, *args, **options):
        limit = options['limit']
        delay = options['delay']
        
        self.stdout.write(f"Starting to process email queue (Limit: {limit}, Delay: {delay}s)...")
        
        # Get campaigns that are ready to send (scheduled for past or present)
        now = timezone.now()
        active_campaigns = Campaign.objects.filter(
            status__in=['scheduled', 'sending'],
            scheduled_for__lte=now
        )
        
        if not active_campaigns.exists():
            self.stdout.write(f"No campaigns scheduled to send at this time ({now}).")
            return

        emails_sent = 0
        
        with get_connection() as connection:
            for campaign in active_campaigns:
                if campaign.status == 'scheduled':
                    campaign.status = 'sending'
                    campaign.save()
                
                # Get pending recipients for this campaign
                # Order by id to ensure we process them systematically
                recipients = campaign.recipients.filter(status='pending')[:limit - emails_sent]
                
                if not recipients.exists():
                    # Check if all are done (or if campaign was cancelled mid-flight)
                    campaign.refresh_from_db() # Get fresh status just in case
                    if campaign.status != 'cancelled':
                        campaign.update_counts()
                    continue
                    
                self.stdout.write(f"Processing Campaign: {campaign.name} ({recipients.count()} recipients in this batch)")
                
                # Pre-fetch opted out emails to double check before sending
                opted_out_emails = set(OptOut.objects.values_list('email', flat=True))
                
                for recipient in recipients:
                    if emails_sent >= limit:
                        break
                        
                    # Double check campaign status inside the loop to allow immediate halting
                    campaign.refresh_from_db(fields=['status'])
                    if campaign.status == 'cancelled':
                        self.stdout.write(self.style.WARNING(f"  ⚠️ Campaign '{campaign.name}' was cancelled. Stopping immediately."))
                        break
                        
                    if recipient.email in opted_out_emails:
                        recipient.status = 'opted_out'
                        recipient.save()
                        continue
                        
                    try:
                        context = {
                            'contact_name': recipient.display_contact_name or 'Valued Contact',
                            'company_name': recipient.display_company_name or 'Sample Company Inc.',
                        }
                        html_content = render_campaign_html(campaign, context, preview=False)
                        
                        # Add DPA & Unsubscribe Footer if requested
                        if campaign.include_unsubscribe:
                            # In production, use SITE_URL from settings. For this demo, we'll use a placeholder domain or relative path if requested locally
                            domain = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')
                            unsub_url = f"{domain}{reverse('mass_mailing:unsubscribe', kwargs={'recipient_id': recipient.id})}"
                            interested_url = f"{domain}{reverse('mass_mailing:interested', kwargs={'recipient_id': recipient.id})}"
                            
                            footer = f"""
                            <br><br><hr>
                            <div style="margin:16px 0 18px 0; text-align: center;">
                                <a href="{interested_url}" style="display:inline-block;background:#16a34a;color:#ffffff;text-decoration:none;padding:10px 18px;border-radius:6px;font-weight:700;font-size:14px;">Interested - Send More Information</a>
                            </div>
                            <p style="font-size: 11px; color: #666; text-align: center;">
                                This email was sent to you because you are a valued contact of <strong>Micro Image International Corp.</strong>
                                <br>In accordance with the Data Privacy Act of 2012 (R.A. 10173), you have the right to opt-out of receiving these marketing communications.
                                <br><br>
                                <a href="{unsub_url}">Click here to Unsubscribe safely</a>
                            </p>
                            """
                            html_content = insert_before_body_close(html_content, footer)
                            
                        # Plain text alternative
                        from django.utils.html import strip_tags
                        if campaign.template_type == 'product_of_week':
                            text_content = "Product of the Week from Micro Image International Corp. Please view this email in HTML to see the featured product image."
                        else:
                            text_content = strip_tags(html_content)
                        
                        msg = EmailMultiAlternatives(
                            subject=campaign.subject,
                            body=text_content,
                            from_email=campaign.created_by.email,
                            to=[recipient.email],
                            connection=connection
                        )
                        msg.attach_alternative(html_content, "text/html")
                        for asset in campaign.inline_assets():
                            if not asset.file:
                                continue
                            asset.file.open('rb')
                            content = asset.file.read()
                            asset.file.close()
                            content_type = getattr(asset.file.file, 'content_type', '') or getattr(asset.file, 'content_type', '') or 'image/png'
                            subtype = content_type.split('/')[-1]
                            image = MIMEImage(content, _subtype=subtype)
                            image.add_header('Content-ID', f"<campaign-asset-{asset.id}>")
                            image.add_header('Content-Disposition', 'inline', filename=asset.display_name or asset.file.name.rsplit('/', 1)[-1])
                            msg.attach(image)
                        for asset in campaign.attachment_assets():
                            if not asset.file:
                                continue
                            filename = asset.display_name or asset.file.name.rsplit('/', 1)[-1]
                            asset.file.open('rb')
                            content = asset.file.read()
                            asset.file.close()
                            msg.attach(filename, content, 'application/octet-stream')
                        msg.send()
                        
                        recipient.status = 'sent'
                        recipient.sent_at = timezone.now()
                        recipient.save()
                        emails_sent += 1
                        
                        self.stdout.write(f"  ✓ Sent to {recipient.email}")
                        
                        # Log Sales Activity
                        self.log_sales_activity(campaign, recipient)
                        
                        # Rate limiting delay
                        if delay > 0 and emails_sent < limit:
                            time.sleep(delay)
                            
                    except Exception as e:
                        recipient.status = 'failed'
                        recipient.error_message = str(e)
                        recipient.save()
                        self.stdout.write(self.style.ERROR(f"  ✗ Failed sending to {recipient.email}: {e}"))
                
                campaign.update_counts()

        self.stdout.write(self.style.SUCCESS(f"Finished processing. Total emails sent: {emails_sent}"))

    def log_sales_activity(self, campaign, recipient):
        """Log the email as a sales activity and award points"""
        try:
            # 1. Create/Get Activity Type
            activity_type, _ = ActivityType.objects.get_or_create(
                name='Email Campaign',
                defaults={
                    'description': 'Mass mailing campaign sent to customers',
                    'icon': 'fas fa-mail-bulk',
                    'color': 'info',
                    'requires_customer': False
                }
            )
            
            # 2. Create Sales Activity
            activity = SalesActivity.objects.create(
                title=f"Campaign Email: {campaign.subject}",
                description=f"Sent via mass mailing campaign '{campaign.name}'",
                activity_type=activity_type,
                salesperson=campaign.created_by,
                customer=recipient.customer,
                status='completed',
                priority='medium',
                scheduled_start=timezone.now(),
                scheduled_end=timezone.now(),
                actual_start=timezone.now(),
                actual_end=timezone.now()
            )
            
            # 3. Create Email Details
            EmailActivity.objects.create(
                sales_activity=activity,
                email_type='newsletter',
                subject=campaign.subject,
                recipients=recipient.email,
                has_attachments=campaign.assets.exists()
            )
            
            # 4. Gamification Points
            points = 5 # Standard points for sending a campaign email
            
            # Update user profile
            profile, _ = GamificationProfile.objects.get_or_create(user=campaign.created_by)
            profile.add_points(points)
            
            # Log points
            PointLog.objects.create(
                user=campaign.created_by,
                action_type='sent_campaign_email',
                points_amount=points,
                content_type=None, # Optional: could link to SalesActivity content type
                object_id=activity.id
            )
            
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  ⚠️ Failed to log activity/points: {e}"))
