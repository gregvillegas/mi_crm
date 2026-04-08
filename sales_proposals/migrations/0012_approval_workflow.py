from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):
    dependencies = [
        ('sales_proposals', '0011_proposal_contact_email_proposal_contact_name_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='proposal',
            name='approval_status',
            field=models.CharField(choices=[('not_required', 'Not Required'), ('pending', 'Pending'), ('in_progress', 'In Progress'), ('approved', 'Approved'), ('rejected', 'Rejected')], default='not_required', max_length=20),
        ),
        migrations.AddField(
            model_name='proposal',
            name='approval_required',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='proposal',
            name='approval_submitted_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='proposal',
            name='approved_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='proposal',
            name='approval_total_php',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name='proposal',
            name='approval_version',
            field=models.IntegerField(default=0),
        ),
        migrations.CreateModel(
            name='ProposalApprovalStep',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('level', models.PositiveIntegerField()),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')], default='pending', max_length=20)),
                ('decided_at', models.DateTimeField(blank=True, null=True)),
                ('comment', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('approver', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='proposal_approvals', to=settings.AUTH_USER_MODEL)),
                ('proposal', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='approval_steps', to='sales_proposals.proposal')),
            ],
            options={
                'ordering': ['level', 'created_at'],
                'unique_together': {('proposal', 'level')},
            },
        ),
    ]

