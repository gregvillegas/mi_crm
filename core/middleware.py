from django.shortcuts import redirect
from django.urls import reverse
from .models import SiteSetting
from allauth.mfa.utils import is_mfa_enabled

class MFARequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Check if MFA is globally required
            setting = SiteSetting.objects.first()
            if setting and setting.mfa_required:
                # Exclude certain paths to avoid redirect loops
                exempt_paths = [
                    reverse('mfa_index'),
                    reverse('mfa_activate_totp'),
                    reverse('mfa_deactivate_totp'),
                    reverse('logout'),
                    '/admin/',
                    '/static/',
                    '/media/',
                ]
                
                # Also check if it's an allauth MFA path
                is_exempt = any(request.path.startswith(path) for path in exempt_paths)
                
                if not is_exempt and not is_mfa_enabled(request.user):
                    return redirect('mfa_index')

        response = self.get_response(request)
        return response
