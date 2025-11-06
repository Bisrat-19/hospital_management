from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AuthViewSet, UserAdminViewSet

router = DefaultRouter()

router.register(r'', UserAdminViewSet, basename='user')
router.register(r'', AuthViewSet, basename='auth')

urlpatterns = [
    path('', include(router.urls)),
]
