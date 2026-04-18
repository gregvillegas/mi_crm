from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('customers', '0019_customercreaterequest_requester_seen_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='customer',
            name='auto_inactive_flag',
            field=models.BooleanField(default=False, help_text='System-managed flag when no sales activity is created within the configured period'),
        ),
        migrations.AddField(
            model_name='customer',
            name='is_millionaire_account',
            field=models.BooleanField(default=False, help_text='System-managed flag based on cumulative won revenue above 1,000,000'),
        ),
        migrations.AddField(
            model_name='customer',
            name='last_sales_activity_at',
            field=models.DateTimeField(blank=True, help_text='Most recent sales activity creation date for this customer', null=True),
        ),
        migrations.AddField(
            model_name='customer',
            name='lifetime_won_revenue',
            field=models.DecimalField(decimal_places=2, default=0, help_text='System-managed cumulative won revenue from sales funnel entries', max_digits=14),
        ),
        migrations.AddField(
            model_name='customer',
            name='status_last_synced_at',
            field=models.DateTimeField(blank=True, help_text='Last time automatic customer status fields were synchronized', null=True),
        ),
        migrations.AddIndex(
            model_name='customer',
            index=models.Index(fields=['is_millionaire_account'], name='customers_c_is_mill_8be6fd_idx'),
        ),
        migrations.AddIndex(
            model_name='customer',
            index=models.Index(fields=['auto_inactive_flag'], name='customers_c_auto_in_d34b53_idx'),
        ),
    ]
