from rest_framework import viewsets, permissions
from rest_framework.response import Response
from rest_framework import status
from django.core.cache import cache
from django.conf import settings
from .models import Patient
from .serializers import PatientSerializer

CACHE_TTL = getattr(settings, 'CACHE_TTL', 300)


class IsReceptionist(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and getattr(request.user, 'role', None) == 'receptionist'


class IsAdminOrReceptionist(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and getattr(request.user, 'role', None) in ['admin', 'receptionist']


class IsAdminRecDoctor(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and getattr(request.user, 'role', None) in ['admin', 'receptionist', 'doctor']


class PatientViewSet(viewsets.ModelViewSet):
    queryset = Patient.objects.all().order_by('-created_at')
    serializer_class = PatientSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update']:
            permission_classes = [IsReceptionist]
        elif self.action == 'list':
            permission_classes = [IsAdminOrReceptionist]
        elif self.action == 'retrieve':
            permission_classes = [IsAdminRecDoctor]
        elif self.action == 'destroy':
            permission_classes = [permissions.IsAdminUser]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [p() for p in permission_classes]

    # Cached list of patients
    def list(self, request, *args, **kwargs):
        cache_key = "all_patients"
        data = cache.get(cache_key)
        if not data:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            data = serializer.data
            cache.set(cache_key, data, timeout=CACHE_TTL)
            print("Cache MISS — patients list")
        else:
            print("Cache HIT — patients list")
        return Response(data, status=status.HTTP_200_OK)

    # Cached single patient retrieval
    def retrieve(self, request, pk=None, *args, **kwargs):
        cache_key = f"patient_{pk}"
        data = cache.get(cache_key)
        if not data:
            try:
                patient = self.get_queryset().get(pk=pk)
            except Patient.DoesNotExist:
                return Response({"error": "Patient not found"}, status=status.HTTP_404_NOT_FOUND)
            serializer = self.get_serializer(patient)
            data = serializer.data
            cache.set(cache_key, data, timeout=CACHE_TTL)
            print(f"Cache MISS — patient {pk}")
        else:
            print(f"Cache HIT — patient {pk}")
        return Response(data, status=status.HTTP_200_OK)

    # Invalidate caches on create/update/partial_update/destroy
    def perform_create(self, serializer):
        instance = serializer.save()
        cache.delete("all_patients")
        return instance

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        pk = kwargs.get("pk")
        cache.delete("all_patients")
        cache.delete(f"patient_{pk}")
        return response

    def partial_update(self, request, *args, **kwargs):
        response = super().partial_update(request, *args, **kwargs)
        pk = kwargs.get("pk")
        cache.delete("all_patients")
        cache.delete(f"patient_{pk}")
        return response

    def destroy(self, request, *args, **kwargs):
        pk = kwargs.get("pk")
        response = super().destroy(request, *args, **kwargs)
        cache.delete("all_patients")
        cache.delete(f"patient_{pk}")
        return response