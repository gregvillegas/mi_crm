from django.urls import path
from . import views

app_name = 'sales_funnel'

urlpatterns = [
    # Main dashboard
    path('', views.funnel_dashboard, name='dashboard'),
    path('export/', views.export_funnel_report, name='export'),
    
    # Entry management (CRUD)
    path('add/', views.add_funnel_entry, name='add_entry'),
    path('edit/<int:entry_id>/', views.edit_funnel_entry, name='edit_entry'),
    path('delete/<int:entry_id>/', views.delete_funnel_entry, name='delete_entry'),
    path('import/', views.import_funnel_entries, name='import_entries'),
    path('sample-csv/', views.download_sample_csv, name='download_sample_csv'),
    path('normalize-stages/', views.normalize_funnel_stages, name='normalize_stages'),
    
    # AJAX endpoints
    path('update-stage/<int:entry_id>/', views.update_entry_stage, name='update_stage'),
    path('close/<int:entry_id>/', views.close_entry, name='close_entry'),
    
    # History and statistics
    path('deals-history/', views.deals_history, name='deals_history'),
    # Maintenance
    path('clear-stage/', views.clear_stage_entries, name='clear_stage'),
]
