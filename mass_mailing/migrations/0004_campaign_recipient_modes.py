from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('mass_mailing', '0003_media_library_and_campaign_asset_link'),
    ]

    operations = [
        migrations.AddField(
            model_name='campaign',
            name='recipient_mode',
            field=models.CharField(
                choices=[('crm', 'CRM Customers'), ('csv', 'CSV Upload'), ('manual', 'Manual Entry')],
                default='crm',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='campaignrecipient',
            name='company_name',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='campaignrecipient',
            name='contact_name',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='campaignrecipient',
            name='position',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='campaignrecipient',
            name='source_type',
            field=models.CharField(default='customer', max_length=20),
        ),
        migrations.AlterField(
            model_name='campaignrecipient',
            name='customer',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='customers.customer'),
        ),
    ]
