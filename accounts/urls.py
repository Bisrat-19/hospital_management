from django.urls import path
from .views.auth_views import login_view, register_view
from .views.profile_views import profile_view
from .views.admin_views import (
    list_users_view,
    get_user_view,
    update_user_view,
    delete_user_view,
)

urlpatterns = [
    path('register/', register_view, name='register'),
    path('login/', login_view, name='login'),
    path('profile/', profile_view, name='profile'),

    # admin user endpoints
    path('users/', list_users_view, name='list_users'),
    path('users/<int:pk>/', get_user_view, name='get_user'),
    path('users/<int:pk>/update/', update_user_view, name='update_user'),
    path('users/<int:pk>/delete/', delete_user_view, name='delete_user'),
]
