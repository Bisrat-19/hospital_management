import logging
from rest_framework import viewsets, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework import status
from django.utils import timezone
from django.core.cache import cache
from django.conf import settings
from .models import Patient
from .serializers import PatientSerializer

CACHE_TTL = getattr(settings, 'CACHE_TTL', 300)
logger = logging.getLogger(__name__)


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
            logger.debug("patients.list cache miss; cached %d records", len(data))
        else:
            logger.debug("patients.list cache hit")
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
            logger.debug("patients.retrieve cache miss for id=%s", pk)
        else:
            logger.debug("patients.retrieve cache hit for id=%s", pk)
        return Response(data, status=status.HTTP_200_OK)

    # Invalidate caches on create/update/partial_update/destroy
    def perform_create(self, serializer):
        instance = serializer.save()
        cache.delete("all_patients")
        
        # Clear appointment caches since a new appointment is created with the patient
        cache.delete("appointments_grouped")
        today = timezone.now().date().isoformat()
        if instance.assigned_doctor:
            cache.delete(f"appointments_today_doctor_{instance.assigned_doctor.id}_{today}")
        cache.delete(f"appointments_today_all_{today}")
    
    def perform_update(self, serializer):
        instance = serializer.save()
        cache.delete("all_patients")
        cache.delete(f"patient_{instance.pk}")

    def perform_destroy(self, instance):
        pk = instance.pk
        instance.delete()
        cache.delete("all_patients")
        cache.delete(f"patient_{pk}")

    @action(detail=False, methods=['get'])
    def today(self, request):
        today = timezone.now().date()
        queryset = self.get_queryset().filter(created_at__date=today)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)