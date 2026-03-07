from django.urls import path
from . import views

urlpatterns = [
    path('', views.proposal_list, name='proposal_list'),
    path('create/', views.proposal_create, name='proposal_create'),
    path('<int:pk>/', views.proposal_detail, name='proposal_detail'),
    path('<int:pk>/edit/', views.proposal_update, name='proposal_update'),
    path('<int:pk>/delete/', views.proposal_delete, name='proposal_delete'),
    path('<int:pk>/pdf/', views.proposal_pdf, name='proposal_pdf'),
    path('<int:pk>/email/', views.proposal_email, name='proposal_email'),
]
