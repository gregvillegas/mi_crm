from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("mass_mailing", "0005_campaign_crm_leads"),
    ]

    operations = [
        migrations.AddField(
            model_name="campaign",
            name="interested_redirect_url",
            field=models.URLField(blank=True),
        ),
        migrations.AddField(
            model_name="campaignrecipient",
            name="interested_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]

