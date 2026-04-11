from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('mass_mailing', '0002_campaign_builder_and_assets'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='MediaLibraryAsset',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('file', models.FileField(upload_to='campaign_library/')),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('uploaded_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='uploaded_media_library_assets', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Media Library Asset',
                'verbose_name_plural': 'Media Library Assets',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddField(
            model_name='campaignasset',
            name='library_asset',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='campaign_assets', to='mass_mailing.medialibraryasset'),
        ),
    ]

