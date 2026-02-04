from django.urls import path
from . import views

urlpatterns = [
    path('', views.team_list, name='team_list'),
    path('create/', views.create_team, name='create_team'),
    path('<int:pk>/groups/', views.team_groups, name='team_groups'),
    path('groups/', views.group_list, name='group_list'),
    path('groups/create/', views.create_group, name='create_group'),
    path('groups/<int:pk>/members/', views.group_members, name='group_members'),
    path('groups/<int:pk>/edit/', views.edit_group, name='edit_group'),
    path('memberships/<int:pk>/quota/', views.update_member_quota, name='update_member_quota'),
    path('groups/<int:pk>/commitment/', views.update_supervisor_commitment, name='update_supervisor_commitment'),
    path('groups/<int:pk>/commitment/history/', views.commitment_history, name='commitment_history'),
    path('groups/<int:pk>/contribution/', views.update_personal_contribution, name='update_personal_contribution'),
    path('teams/<int:pk>/asm-target/', views.update_asm_target, name='update_asm_target'),
    path('quota/<int:user_id>/', views.update_role_quota, name='update_role_quota'),
]
