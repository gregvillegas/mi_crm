from django.urls import path
from . import views

app_name = 'lead_generation'

urlpatterns = [
    # Dashboard and main views
    path('', views.lead_dashboard, name='dashboard'),
    path('leads/', views.lead_list, name='lead_list'),
    path('my-leads/', views.my_leads, name='my_leads'),
    
    # Lead CRUD
    path('leads/create/', views.lead_create, name='lead_create'),
    path('leads/<int:lead_id>/', views.lead_detail, name='lead_detail'),
    path('leads/<int:lead_id>/edit/', views.lead_edit, name='lead_edit'),
    
    # Lead actions
    path('leads/<int:lead_id>/convert/', views.convert_lead, name='convert_lead'),
    path('leads/<int:lead_id>/activity/', views.add_lead_activity, name='add_lead_activity'),
    path('leads/<int:lead_id>/update-status/', views.update_lead_status, name='update_status'),
    
    # Lead sources
    path('sources/', views.lead_sources, name='lead_sources'),
    path('sources/create/', views.lead_source_create, name='lead_source_create'),
    
    # Analytics
    path('analytics/', views.analytics_dashboard, name='analytics'),
    
    # Hot leads
    path('hot-leads/', views.hot_leads, name='hot_leads'),
    
    # Export
    path('export/', views.lead_export, name='lead_export'),
]
