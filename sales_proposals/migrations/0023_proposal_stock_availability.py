from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sales_proposals', '0022_proposal_sales_margin_pct'),
    ]

    operations = [
        migrations.AddField(
            model_name='proposal',
            name='stock_availability',
            field=models.CharField(
                blank=True,
                choices=[
                    ('', '---------'),
                    ('ON-STOCK 3 TO 5 WORKING DAYS', 'ON-STOCK 3 TO 5 WORKING DAYS'),
                    ('LIMITED STOCK', 'LIMITED STOCK'),
                    ('ORDER BASIS (30 TO 45 WORKING DAYS)', 'ORDER BASIS (30 TO 45 WORKING DAYS)'),
                    ('ORDER BASIS (60 TO 90 WORKING DAYS)', 'ORDER BASIS (60 TO 90 WORKING DAYS)'),
                    ('ORDER BASIS (90 TO 120 WORKING DAYS)', 'ORDER BASIS (90 TO 120 WORKING DAYS)'),
                    ('ORDER BASIS (7 TO 10 WORKING DAYS)', 'ORDER BASIS (7 TO 10 WORKING DAYS)'),
                    ('CONFIG TO ORDER (30 TO 45 WORKING DAYS)', 'CONFIG TO ORDER (30 TO 45 WORKING DAYS)'),
                    ('CONFIG TO ORDER (60 TO 90 WORKING DAYS)', 'CONFIG TO ORDER (60 TO 90 WORKING DAYS)'),
                    ('CONFIG TO ORDER (90 TO 120 WORKING DAYS)', 'CONFIG TO ORDER (90 TO 120 WORKING DAYS)'),
                ],
                default='',
                max_length=80,
            ),
        ),
    ]
