from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):
    dependencies = [
        ('sales_proposals', '0012_approval_workflow'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProposalApprovalTier',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, max_length=100)),
                ('min_amount_php', models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(0)])),
                ('max_amount_php', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ('chain', models.CharField(help_text='Comma-separated roles: supervisor,asm,avp_or_gm', max_length=200)),
                ('order', models.PositiveIntegerField(default=0)),
                ('active', models.BooleanField(default=True)),
            ],
            options={
                'ordering': ['order', 'min_amount_php'],
            },
        ),
    ]

