from django.utils import timezone
from .models import UserActivityLog

class UserActivityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if request.user.is_authenticated:
            # Update last_activity
            request.user.last_activity = timezone.now()
            request.user.save(update_fields=['last_activity'])

            # Log activity (excluding static/media/admin assets if possible)
            path = request.path
            if not (path.startswith('/static/') or path.startswith('/media/')):
                # Get IP Address
                x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
                if x_forwarded_for:
                    ip = x_forwarded_for.split(',')[0]
                else:
                    ip = request.META.get('REMOTE_ADDR')

                UserActivityLog.objects.create(
                    user=request.user,
                    path=path[:255],
                    method=request.method,
                    ip_address=ip,
                    details=f"User visited {path}"
                )

        return response
