# -----------------------------------------------------------------------------
# 7. crm_project/urls.py
# -----------------------------------------------------------------------------
from django.contrib import admin
from django.urls import path, include
from core.views import home, logout_view
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import routers
from users.api import UserViewSet, CustomAuthToken
from crm_project.api_views import SalesFunnelViewSet, ProposalViewSet, SalesActivityViewSet

# API Router
router = routers.DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'funnel', SalesFunnelViewSet, basename='funnel')
router.register(r'proposals', ProposalViewSet, basename='proposals')
router.register(r'activities', SalesActivityViewSet, basename='activities')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include(router.urls)),
    path('api/v1/api-token-auth/', CustomAuthToken.as_view()),
    path('', home, name='home'),
    path('customers/', include('customers.urls')),
    path('users/', include('users.urls')), # <-- ADDED
    path('teams/', include('teams.urls')), # <-- ADDED
    path('funnel/', include('sales_funnel.urls')), # <-- ADDED
    path('sales-monitoring/', include('sales_monitoring.urls')), # <-- ADDED
    path('leads/', include('lead_generation.urls')), # <-- ADDED
    path('files/', include('file_sharing.urls')), # <-- ADDED
    path('proposals/', include('sales_proposals.urls')), # <-- ADDED
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),
    path('logout/', logout_view, name='logout'),
    path('accounts/', include(('django.contrib.auth.urls', 'auth'), namespace='auth')),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
