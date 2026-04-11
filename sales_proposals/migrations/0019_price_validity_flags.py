from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('sales_proposals', '0018_bank_details_per_currency'),
    ]

    operations = [
        migrations.AddField(
            model_name='proposal',
            name='validity_subject_to_prior_sale',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='proposal',
            name='validity_availability_at_order',
            field=models.BooleanField(default=False),
        ),
    ]

