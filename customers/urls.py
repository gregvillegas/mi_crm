# -----------------------------------------------------------------------------
# 8. customers/urls.py
# -----------------------------------------------------------------------------
from django.urls import path
from . import views

urlpatterns = [
    path('', views.customer_list, name='customer_list'),
    path('delinquent/', views.delinquent_list, name='delinquent_list'),
    path('delinquent/add/', views.create_delinquency, name='create_delinquency'),
    path('delinquent/import/', views.import_delinquencies, name='import_delinquencies'),
    path('delinquent/sample-csv/', views.download_delinquency_sample_csv, name='download_delinquency_sample_csv'),
    path('delinquent/export/', views.export_delinquencies, name='export_delinquencies'),
    path('add/', views.create_customer, name='create_customer'),
    path('<int:pk>/transfer/', views.transfer_customer, name='transfer_customer'),
    path('<int:pk>/toggle-vip/', views.toggle_customer_vip, name='toggle_customer_vip'),
    path('<int:pk>/toggle-active/', views.toggle_customer_active, name='toggle_customer_active'),
    path('<int:pk>/history/', views.customer_history, name='customer_history'),
    path('export/', views.export_customers, name='export_customers'),
    path('import/', views.import_customers, name='import_customers'),
    path('sample-csv/', views.download_sample_csv, name='download_sample_csv'),
    
    # Admin backup and restore functionality
    path('<int:pk>/edit/', views.edit_customer, name='edit_customer'),
    path('<int:pk>/backups/', views.customer_backups, name='customer_backups'),
    path('<int:pk>/backup/', views.create_manual_backup, name='create_manual_backup'),
    path('<int:customer_pk>/restore/<int:backup_pk>/', views.restore_customer, name='restore_customer'),
    path('backups-overview/', views.backup_overview, name='backup_overview'),
]
