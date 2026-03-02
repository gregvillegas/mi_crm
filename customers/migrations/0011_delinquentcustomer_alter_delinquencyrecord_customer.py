from django.db import migrations, models
import django.db.models.deletion


def forwards_copy_to_delinquent(apps, schema_editor):
    DelinquentCustomer = apps.get_model('customers', 'DelinquentCustomer')
    DelinquencyRecord = apps.get_model('customers', 'DelinquencyRecord')
    Customer = apps.get_model('customers', 'Customer')
    db_alias = schema_editor.connection.alias
    for rec in DelinquencyRecord.objects.using(db_alias).all():
        # rec.customer currently points to Customer (pre-migration state)
        try:
            cust = Customer.objects.using(db_alias).get(pk=rec.customer_id)
        except Customer.DoesNotExist:
            cust = None
        if cust:
            dcustomer, _ = DelinquentCustomer.objects.using(db_alias).get_or_create(
                company_name=cust.company_name,
                defaults={
                    'contact_person_name': cust.contact_person_name,
                    'email': cust.email or '',
                }
            )
        else:
            # Fallback: create minimal delinquent customer
            dcustomer, _ = DelinquentCustomer.objects.using(db_alias).get_or_create(
                company_name='Unknown'
            )
        rec.new_customer_id = dcustomer.id
        rec.save(update_fields=['new_customer'])


def backwards_noop(apps, schema_editor):
    # Intentionally left as a no-op; reversing would risk data loss
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('customers', '0010_delinquencyrecord_date_delivered_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='DelinquentCustomer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('company_name', models.CharField(max_length=200)),
                ('contact_person_name', models.CharField(blank=True, max_length=200)),
                ('email', models.EmailField(blank=True, max_length=254)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['company_name'],
                'indexes': [
                    models.Index(fields=['company_name'], name='customers_d_company_bbf9fe_idx'),
                    models.Index(fields=['email'], name='customers_d_email_058bea_idx'),
                ],
            },
        ),
        # Add a temporary field to hold new foreign key
        migrations.AddField(
            model_name='delinquencyrecord',
            name='new_customer',
            field=models.ForeignKey(null=True, blank=True, on_delete=django.db.models.deletion.CASCADE, related_name='delinquency_records', to='customers.delinquentcustomer'),
        ),
        migrations.RunPython(forwards_copy_to_delinquent, backwards_noop),
        # Remove old field to Customer
        migrations.RemoveField(
            model_name='delinquencyrecord',
            name='customer',
        ),
        # Rename new_customer -> customer
        migrations.RenameField(
            model_name='delinquencyrecord',
            old_name='new_customer',
            new_name='customer',
        ),
    ]
