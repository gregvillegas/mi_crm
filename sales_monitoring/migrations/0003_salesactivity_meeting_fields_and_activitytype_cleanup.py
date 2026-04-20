from django.db import migrations, models


def normalize_activity_types(apps, schema_editor):
    ActivityType = apps.get_model('sales_monitoring', 'ActivityType')
    SalesActivity = apps.get_model('sales_monitoring', 'SalesActivity')

    def update_activity_type(obj, name, description, icon, color, requires_customer=True):
        obj.name = name
        obj.description = description
        obj.icon = icon
        obj.color = color
        obj.requires_customer = requires_customer
        obj.is_active = True
        obj.save(update_fields=['name', 'description', 'icon', 'color', 'requires_customer', 'is_active'])

    canonical_meeting = ActivityType.objects.filter(name='Client Meeting').first()
    legacy_client_call = ActivityType.objects.filter(name='Client Call').first()
    generic_meeting = ActivityType.objects.filter(name='Meeting').first()

    if legacy_client_call:
        if canonical_meeting and canonical_meeting.pk != legacy_client_call.pk:
            SalesActivity.objects.filter(activity_type_id=legacy_client_call.pk).update(activity_type_id=canonical_meeting.pk)
            legacy_client_call.delete()
        else:
            update_activity_type(
                legacy_client_call,
                'Client Meeting',
                'Client-facing meetings such as initial meetings, demos, proposal presentations, negotiations, and closing meetings.',
                'fas fa-handshake',
                'success',
            )
            canonical_meeting = legacy_client_call

    if generic_meeting:
        if canonical_meeting and canonical_meeting.pk != generic_meeting.pk:
            SalesActivity.objects.filter(activity_type_id=generic_meeting.pk).update(activity_type_id=canonical_meeting.pk)
            generic_meeting.delete()
        else:
            update_activity_type(
                generic_meeting,
                'Client Meeting',
                'Client-facing meetings such as initial meetings, demos, proposal presentations, negotiations, and closing meetings.',
                'fas fa-handshake',
                'success',
            )
            canonical_meeting = generic_meeting

    phone_call = ActivityType.objects.filter(name='Phone Call').first()
    if phone_call:
        update_activity_type(
            phone_call,
            'Phone Call',
            'Cold calls, warm calls, follow-up calls, support calls, and other customer phone conversations.',
            'fas fa-phone',
            'primary',
        )


def reverse_normalize_activity_types(apps, schema_editor):
    ActivityType = apps.get_model('sales_monitoring', 'ActivityType')
    client_meeting = ActivityType.objects.filter(name='Client Meeting').first()
    if client_meeting:
        client_meeting.name = 'Meeting'
        client_meeting.description = 'In-person or virtual meetings with customers'
        client_meeting.icon = 'fas fa-handshake'
        client_meeting.color = 'success'
        client_meeting.requires_customer = True
        client_meeting.save(update_fields=['name', 'description', 'icon', 'color', 'requires_customer'])


class Migration(migrations.Migration):

    dependencies = [
        ('sales_monitoring', '0002_proofofconcept'),
    ]

    operations = [
        migrations.AddField(
            model_name='salesactivity',
            name='engineer_required',
            field=models.BooleanField(default=False, help_text='Whether engineering support is required for this client meeting'),
        ),
        migrations.AddField(
            model_name='salesactivity',
            name='meeting_notification_sent_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='salesactivity',
            name='meeting_notification_sent_for',
            field=models.DateTimeField(blank=True, help_text='Scheduled start datetime for which the last meeting reminder was sent', null=True),
        ),
        migrations.RunPython(normalize_activity_types, reverse_normalize_activity_types),
    ]
