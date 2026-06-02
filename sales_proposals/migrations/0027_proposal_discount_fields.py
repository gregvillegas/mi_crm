from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sales_proposals', '0026_alter_proposal_usd_beneficiary_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='proposal',
            name='show_discount',
            field=models.BooleanField(default=False, help_text='Show discount line in the proposal PDF'),
        ),
        migrations.AddField(
            model_name='proposal',
            name='discount_amount',
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text='Manual discount amount (informational; does not change totals).',
                max_digits=12,
                validators=[MinValueValidator(Decimal('0.00'))],
            ),
        ),
    ]

