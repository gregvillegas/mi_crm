from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):
    dependencies = [
        ('customers', '0016_alter_customercontact_unique_together_and_more'),
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='CustomerCreateRequest',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('company_name', models.CharField(max_length=100)),
                ('contact_person_name', models.CharField(max_length=100)),
                ('contact_person_position', models.CharField(blank=True, max_length=100)),
                ('email', models.EmailField(max_length=254)),
                ('phone_number', models.CharField(blank=True, max_length=20)),
                ('address', models.TextField(blank=True)),
                ('industry', models.CharField(blank=True, max_length=50)),
                ('territory', models.CharField(blank=True, max_length=50)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')], default='pending', max_length=10)),
                ('similar_matches', models.JSONField(blank=True, help_text='List of similar existing customers with similarity scores', null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('decision_notes', models.TextField(blank=True)),
                ('requested_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='customer_create_requests', to=settings.AUTH_USER_MODEL)),
                ('reviewed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='customer_create_reviews', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='customercreaterequest',
            index=models.Index(fields=['status'], name='customers_c_status_5f0a41_idx'),
        ),
        migrations.AddIndex(
            model_name='customercreaterequest',
            index=models.Index(fields=['company_name'], name='customers_c_company_72f64e_idx'),
        ),
    ]

