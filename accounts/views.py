import logging
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.core.cache import cache
from django.conf import settings
from .serializers import UserSerializer, RegisterSerializer, LoginSerializer, ChangePasswordSerializer
from .models import User
from core.mixins import CacheResponseMixin, CacheInvalidationMixin

CACHE_TTL = getattr(settings, 'CACHE_TTL', 300)
logger = logging.getLogger(__name__)


class UserAdminViewSet(CacheResponseMixin, CacheInvalidationMixin, viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    queryset = User.objects.all()
    serializer_class = UserSerializer
    http_method_names = ['get', 'put', 'patch', 'delete']
    cache_key_prefix = "user"

    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return RegisterSerializer
        return UserSerializer

    def get_cache_keys_to_invalidate(self, instance):
        return [
            f"user_{instance.id}",
            "all_users",
            f"user_profile_{instance.id}"
        ]

    @action(detail=False, methods=['get', 'patch'], permission_classes=[permissions.IsAuthenticated])
    def profile(self, request):
        user = request.user
        cache_key = f"user_profile_{user.id}"

        if request.method == 'PATCH':
            serializer = UserSerializer(user, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                self._invalidate_cache(user)
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        profile_data = cache.get(cache_key)
        if not profile_data:
            serializer = UserSerializer(user)
            profile_data = serializer.data
            cache.set(cache_key, profile_data, timeout=CACHE_TTL)
            logger.debug("accounts.profile cache miss for id=%s", user.id)
        else:
            logger.debug("accounts.profile cache hit for id=%s", user.id)

        return Response(profile_data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['patch'], url_path='change-password', permission_classes=[permissions.IsAuthenticated])
    def change_password(self, request):
        user = request.user
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request, "user": user})
        serializer.is_valid(raise_exception=True)
        serializer.save()

        self._invalidate_cache(user)
        return Response({"detail": "Password updated successfully"}, status=status.HTTP_200_OK)


class AuthViewSet(CacheInvalidationMixin, viewsets.ViewSet):
    def get_cache_keys_to_invalidate(self, instance):
        return ["all_users"]

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
            return Response(serializer.get_token_data())
        return Response(serializer.errors, status=status.HTTP_401_UNAUTHORIZED)

    