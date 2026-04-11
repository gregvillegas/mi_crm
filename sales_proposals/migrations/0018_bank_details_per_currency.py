from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('sales_proposals', '0016_alter_proposalattachment_id_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='proposal',
            name='php_bank_name',
            field=models.CharField(default='BDO Unibank, Inc.', max_length=200),
        ),
        migrations.AddField(
            model_name='proposal',
            name='php_account_name',
            field=models.CharField(default='MICRO IMAGE INTERNATIONAL CORP.', max_length=200),
        ),
        migrations.AddField(
            model_name='proposal',
            name='php_account_number',
            field=models.CharField(default='0123 0001 0002 1111', max_length=100),
        ),
        migrations.AddField(
            model_name='proposal',
            name='php_account_type',
            field=models.CharField(default='Current Account / Checking Account', max_length=200),
        ),
        migrations.AddField(
            model_name='proposal',
            name='php_branch',
            field=models.CharField(default='Banco De Oro - Salcedo Dela Rosa Branch', max_length=200),
        ),
        migrations.AddField(
            model_name='proposal',
            name='usd_beneficiary_name',
            field=models.CharField(default='MICROIMAGE INTERNATIONAL CORP.', max_length=200),
        ),
        migrations.AddField(
            model_name='proposal',
            name='usd_beneficiary_address',
            field=models.CharField(default='Unit 101 Legaspi Suites Bldg., 178 Salcedo St., Makati City', max_length=300),
        ),
        migrations.AddField(
            model_name='proposal',
            name='usd_account_number',
            field=models.CharField(default='0123 0001 0002 1111', max_length=100),
        ),
        migrations.AddField(
            model_name='proposal',
            name='usd_bank_address',
            field=models.CharField(default='G/F State Condominium 1 Building, Salcedo Street, Legaspi Village, Makati, Philippines', max_length=300),
        ),
        migrations.AddField(
            model_name='proposal',
            name='usd_swift_code',
            field=models.CharField(default='BOPIPHMM', max_length=50),
        ),
    ]
