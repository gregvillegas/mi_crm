from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('sales_proposals', '0013_approval_tiers'),
    ]

    operations = [
        migrations.AddField(
            model_name='proposalitem',
            name='warranty',
            field=models.CharField(blank=True, help_text='Per-item warranty (e.g., 1 year parts/labor)', max_length=150),
        ),
    ]

