from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):
    dependencies = [
        ('sales_proposals', '0014_proposalitem_warranty'),
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='proposalitem',
            name='margin_pct',
            field=models.DecimalField(blank=True, decimal_places=2, help_text='Stored margin percentage for display consistency', max_digits=6, null=True),
        ),
        migrations.CreateModel(
            name='ProposalAttachment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(upload_to='proposal_attachments/')),
                ('display_name', models.CharField(blank=True, max_length=200)),
                ('include_in_email', models.BooleanField(default=False)),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('proposal', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attachments', to='sales_proposals.proposal')),
                ('uploaded_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='ProposalChangeLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('changed_at', models.DateTimeField(auto_now_add=True)),
                ('summary', models.TextField(blank=True)),
                ('details', models.JSONField(blank=True, null=True)),
                ('changed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('proposal', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='change_logs', to='sales_proposals.proposal')),
            ],
        ),
    ]

