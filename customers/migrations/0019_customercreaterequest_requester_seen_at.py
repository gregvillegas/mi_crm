from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('customers', '0018_rename_customers_c_status_5f0a41_idx_customers_c_status_34cf10_idx_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='customercreaterequest',
            name='requester_seen_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
