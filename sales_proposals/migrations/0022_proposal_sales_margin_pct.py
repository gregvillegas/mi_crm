from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sales_proposals', '0021_price_validity_mode'),
    ]

    operations = [
        migrations.AddField(
            model_name='proposal',
            name='sales_margin_pct',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('0.00'),
                help_text='Internal total-level salesperson margin percentage.',
                max_digits=6,
                validators=[MinValueValidator(Decimal('0.00'))],
            ),
        ),
    ]
