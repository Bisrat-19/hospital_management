import logging
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.core.cache import cache
from django.conf import settings
from .serializers import UserSerializer, RegisterSerializer, LoginSerializer, ChangePasswordSerializer
from .models import User
from core.mixins import CacheResponseMixin

CACHE_TTL = getattr(settings, 'CACHE_TTL', 300)
logger = logging.getLogger(__name__)


class UserAdminViewSet(CacheResponseMixin, viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    queryset = User.objects.all()
    serializer_class = UserSerializer
    http_method_names = ['get', 'put', 'patch', 'delete']
    cache_key_prefix = "user"

    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return RegisterSerializer
        return UserSerializer

    @action(detail=False, methods=['get', 'patch'], permission_classes=[permissions.IsAuthenticated])
    def profile(self, request):
        if request.method == 'PATCH':
            serializer = UserSerializer(request.user, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                self._invalidate_cache(request.user)
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        profile_data = cache.get(cache_key)

        if not profile_data:
            serializer = UserSerializer(request.user)
            profile_data = serializer.data
            cache.set(cache_key, profile_data, timeout=CACHE_TTL)
            logger.debug("accounts.profile cache miss for id=%s", request.user.id)
        else:
            logger.debug("accounts.profile cache hit for id=%s", request.user.id)

        return Response(profile_data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['patch'], url_path='change-password', permission_classes=[permissions.IsAuthenticated])
    def change_password(self, request):
        user = request.user
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request, "user": user})
        serializer.is_valid(raise_exception=True)
        serializer.save()

        self._invalidate_cache(user)

        return Response({"detail": "Password updated successfully"}, status=status.HTTP_200_OK)

    def perform_update(self, serializer):
        instance = serializer.save()
        self._invalidate_cache(instance)

    def perform_destroy(self, instance):
        pk = instance.pk
        instance.delete()
        self._invalidate_cache(instance)

class AuthViewSet(viewsets.ViewSet):
    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def register(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            self._invalidate_cache(user)
            return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def login(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            token_data = serializer.get_token_data()
            return Response(token_data)
        return Response(serializer.errors, status=status.HTTP_401_UNAUTHORIZED)

    