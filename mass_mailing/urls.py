from django.urls import path
from . import views

app_name = 'mass_mailing'

urlpatterns = [
    path('', views.campaign_list, name='campaign_list'),
    path('create/', views.campaign_create, name='campaign_create'),
    path('<int:pk>/', views.campaign_detail, name='campaign_detail'),
    path('<int:pk>/edit/', views.campaign_edit, name='campaign_edit'),
    path('<int:pk>/cancel/', views.campaign_cancel, name='campaign_cancel'),
    path('<int:pk>/preview/', views.campaign_preview, name='campaign_preview'),
    path('<int:pk>/send/', views.campaign_send, name='campaign_send'),
    path('unsubscribe/<uuid:recipient_id>/', views.unsubscribe, name='unsubscribe'),
]
