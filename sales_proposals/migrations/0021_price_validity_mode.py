from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('sales_proposals', '0020_merge_0019_conflicts'),
    ]

    operations = [
        migrations.AddField(
            model_name='proposal',
            name='price_validity_mode',
            field=models.CharField(
                choices=[
                    ('date_only', 'Valid until selected date'),
                    ('market_notice', 'Use market-condition notice'),
                ],
                default='date_only',
                max_length=20,
            ),
        ),
    ]

