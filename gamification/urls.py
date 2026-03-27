from django.urls import path
from . import views

urlpatterns = [
    path('leaderboard/', views.leaderboard_view, name='leaderboard'),
    path('badges/', views.badge_list_view, name='badges'),
    path('missions/', views.mission_list_view, name='missions_list'),
    path('missions/create/', views.mission_create_view, name='mission_create'),
    path('missions/<int:pk>/edit/', views.mission_edit_view, name='mission_edit'),
]
