from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.core.cache import cache
from django.conf import settings
from .serializers import UserSerializer, RegisterSerializer, LoginSerializer
from .models import User

CACHE_TTL = getattr(settings, 'CACHE_TTL', 300)


class UserAdminViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAdminUser]
    queryset = User.objects.all()
    serializer_class = UserSerializer
    http_method_names = ['get', 'put', 'patch', 'delete']

    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return RegisterSerializer
        return UserSerializer

    # GET all users (cached)
    def list(self, request, *args, **kwargs):
        cache_key = "all_users"
        users = cache.get(cache_key)

        if not users:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            users = serializer.data
            cache.set(cache_key, users, timeout=CACHE_TTL)
            print("Cache MISS — data fetched from DB")
        else:
            print("Cache HIT — data fetched from Redis")

        return Response(users, status=status.HTTP_200_OK)

    # GET single user by ID (cached)
    def retrieve(self, request, pk=None):
        cache_key = f"user_{pk}"
        user_data = cache.get(cache_key)

        if not user_data:
            try:
                user = self.get_queryset().get(pk=pk)
            except User.DoesNotExist:
                return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

            serializer = self.get_serializer(user)
            user_data = serializer.data
            cache.set(cache_key, user_data, timeout=CACHE_TTL)
            print(f"Cache MISS for user {pk}")
        else:
            print(f"Cache HIT for user {pk}")

        return Response(user_data, status=status.HTTP_200_OK)

    # Clear cache when updating or deleting a user
    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        pk = kwargs.get("pk")
        cache.delete(f"user_{pk}")
        cache.delete("all_users")
        return response

    def destroy(self, request, *args, **kwargs):
        pk = kwargs.get("pk")
        response = super().destroy(request, *args, **kwargs)
        cache.delete(f"user_{pk}")
        cache.delete("all_users")
        return response


class AuthViewSet(viewsets.ViewSet):
    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def register(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            # Clear user list cache when new user is created
            cache.delete("all_users")
            return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def login(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            token_data = serializer.get_token_data()
            return Response(token_data)
        return Response(serializer.errors, status=status.HTTP_401_UNAUTHORIZED)

    # Cache the logged-in user’s profile
    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def profile(self, request):
        cache_key = f"profile_{request.user.id}"
        profile_data = cache.get(cache_key)

        if not profile_data:
            serializer = UserSerializer(request.user)
            profile_data = serializer.data
            cache.set(cache_key, profile_data, timeout=CACHE_TTL)
            print(f"Cache MISS for profile {request.user.id}")
        else:
            print(f"Cache HIT for profile {request.user.id}")

        return Response(profile_data, status=status.HTTP_200_OK)
