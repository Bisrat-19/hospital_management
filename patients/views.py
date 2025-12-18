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
from core.mixins import CacheResponseMixin, CacheInvalidationMixin



class IsReceptionist(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and getattr(request.user, 'role', None) == 'receptionist'


class IsAdminOrReceptionist(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and getattr(request.user, 'role', None) in ['admin', 'receptionist']


class IsAdminRecDoctor(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and getattr(request.user, 'role', None) in ['admin', 'receptionist', 'doctor']


class PatientViewSet(CacheResponseMixin, CacheInvalidationMixin, viewsets.ModelViewSet):
    queryset = Patient.objects.all().order_by('-created_at')
    serializer_class = PatientSerializer
    cache_key_prefix = "patient"

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

    def get_cache_keys_to_invalidate(self, instance):
        today = timezone.now().date().isoformat()
        keys = ["all_patients", "all_appointments", "all_treatments", f"appointments_today_all_{today}", f"treatments_today_{today}"]
        
        if instance.pk:
            keys.append(f"patient_{instance.pk}")
            
        if hasattr(instance, 'assigned_doctor') and instance.assigned_doctor:
            keys.append(f"appointments_today_doctor_{instance.assigned_doctor.id}_{today}")
        
        if self.action == 'destroy':
            appointments = instance.appointments.all()
            for appt in appointments:
                if appt.doctor:
                    appt_date = appt.appointment_date.date().isoformat()
                    keys.append(f"appointments_today_doctor_{appt.doctor.id}_{appt_date}")
        
        return list(set(keys)) 

    @action(detail=False, methods=['get'])
    def today(self, request):
        today = timezone.now().date()
        queryset = self.get_queryset().filter(created_at__date=today)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)