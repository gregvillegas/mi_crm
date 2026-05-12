from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sales_funnel', '0005_salesfunnel_proposal'),
    ]

    operations = [
        migrations.AddField(
            model_name='salesfunnel',
            name='brand',
            field=models.CharField(
                blank=True,
                help_text='Optional product or solution brand, e.g. Cisco, IBM, Dell',
                max_length=120,
            ),
        ),
        migrations.AddIndex(
            model_name='salesfunnel',
            index=models.Index(fields=['brand'], name='sales_funnel_brand_idx'),
        ),
    ]
