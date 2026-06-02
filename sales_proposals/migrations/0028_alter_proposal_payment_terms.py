from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sales_proposals', '0027_proposal_discount_fields'),
    ]

    operations = [
        migrations.AlterField(
            model_name='proposal',
            name='payment_terms',
            field=models.TextField(default='30 days', help_text='e.g., 30 days, Cash on Delivery'),
        ),
    ]

