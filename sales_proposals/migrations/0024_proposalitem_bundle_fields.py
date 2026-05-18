from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sales_proposals', '0023_proposal_stock_availability'),
    ]

    operations = [
        migrations.AddField(
            model_name='proposalitem',
            name='bundled_items',
            field=models.TextField(
                blank=True,
                help_text='One bundled component per line. Format: PART NUMBER | Description',
            ),
        ),
        migrations.AddField(
            model_name='proposalitem',
            name='is_bundle',
            field=models.BooleanField(
                default=False,
                help_text='Show bundled component part numbers under this priced item',
            ),
        ),
    ]
