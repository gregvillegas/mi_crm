from django.urls import path
from . import views

urlpatterns = [
    path('customer/<int:customer_id>/create/', views.create_ticket_for_customer, name='create_ticket_for_customer'),
    path('ticket/<int:ticket_id>/', views.ticket_detail, name='ticket_detail'),
    path('ticket/<int:ticket_id>/sync/', views.sync_ticket_status, name='sync_ticket_status'),
]
