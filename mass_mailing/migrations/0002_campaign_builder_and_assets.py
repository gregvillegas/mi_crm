from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('mass_mailing', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='campaign',
            name='template_type',
            field=models.CharField(choices=[('html', 'Custom HTML'), ('hero_promo', 'Hero Promo'), ('product_launch', 'Product Launch'), ('product_of_week', 'Product Of The Week'), ('newsletter_digest', 'Newsletter Digest')], default='html', max_length=30),
        ),
        migrations.AddField(
            model_name='campaign',
            name='hero_headline',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='campaign',
            name='hero_intro',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='campaign',
            name='hero_bullet_1',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='campaign',
            name='hero_bullet_2',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='campaign',
            name='hero_bullet_3',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='campaign',
            name='hero_cta_label',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='campaign',
            name='hero_cta_url',
            field=models.URLField(blank=True),
        ),
        migrations.CreateModel(
            name='CampaignAsset',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(upload_to='campaign_assets/')),
                ('display_name', models.CharField(blank=True, max_length=255)),
                ('embed_inline', models.BooleanField(default=True, help_text='Embed this image inline in the email body')),
                ('sort_order', models.PositiveIntegerField(default=0)),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('campaign', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='assets', to='mass_mailing.campaign')),
                ('uploaded_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='uploaded_campaign_assets', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['sort_order', 'uploaded_at'],
            },
        ),
    ]
