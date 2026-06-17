from django.db import models

class SiteSetting(models.Model):
    mfa_required = models.BooleanField(default=False, help_text="Force all users to use Multi-Factor Authentication")
    
    def __str__(self):
        return "Global Site Settings"

    class Meta:
        verbose_name = "Site Setting"
        verbose_name_plural = "Site Settings"
