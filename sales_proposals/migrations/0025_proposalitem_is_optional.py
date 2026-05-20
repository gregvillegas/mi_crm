from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sales_proposals', '0024_proposalitem_bundle_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='proposalitem',
            name='is_optional',
            field=models.BooleanField(
                default=False,
                help_text='Mark this line as optional so it is excluded from the proposal total',
            ),
        ),
    ]
