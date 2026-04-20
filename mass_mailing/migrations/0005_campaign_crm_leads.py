from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('lead_generation', '0006_alter_leadsource_source_type'),
        ('mass_mailing', '0004_campaign_recipient_modes'),
    ]

    operations = [
        migrations.AlterField(
            model_name='campaign',
            name='recipient_mode',
            field=models.CharField(choices=[('crm', 'CRM Customers'), ('crm_leads', 'CRM Leads'), ('csv', 'CSV Upload'), ('manual', 'Manual Entry')], default='crm', max_length=20),
        ),
        migrations.AddField(
            model_name='campaignrecipient',
            name='lead',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='lead_generation.lead'),
        ),
    ]
