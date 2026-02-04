from django.urls import path
from . import views

urlpatterns = [
    path('add-salesperson/', views.create_salesperson, name='create_salesperson'),
    path('manage/', views.user_management, name='user_management'),
    path('create/', views.create_user, name='create_user'),
    path('edit/<int:user_id>/', views.edit_user, name='edit_user'),
    path('transfer/<int:user_id>/', views.transfer_salesperson, name='transfer_salesperson'),
    path('assign-teamlead/<int:user_id>/', views.assign_teamlead, name='assign_teamlead'),
    path('toggle-active/<int:user_id>/', views.toggle_user_active, name='toggle_user_active'),
    path('export/', views.export_users_json, name='export_users_json'),
]

