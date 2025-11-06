from rest_framework import viewsets, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from django.utils import timezone
from .models import Appointment
from .serializers import AppointmentSerializer


# 🔐 Custom Permissions
class IsDoctor(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and getattr(request.user, 'role', None) == 'doctor'


class IsReceptionist(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and getattr(request.user, 'role', None) == 'receptionist'


class IsAdminOrReceptionist(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and getattr(request.user, 'role', None) in ['admin', 'receptionist']


class AppointmentViewSet(viewsets.ModelViewSet):
    queryset = Appointment.objects.all().order_by('-appointment_date')
    serializer_class = AppointmentSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update']:
            permission_classes = [IsDoctor]  # Doctor creates follow-ups
        elif self.action in ['list']:
            permission_classes = [IsAdminOrReceptionist | IsDoctor]
        elif self.action == 'retrieve':
            permission_classes = [IsAdminOrReceptionist | IsDoctor]
        elif self.action == 'destroy':
            permission_classes = [permissions.IsAdminUser]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [p() for p in permission_classes]

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset().order_by('-appointment_date')
        # If you want doctors to only see their own in list, uncomment next two lines:
        # if getattr(request.user, 'role', None) == 'doctor':
        #     qs = qs.filter(doctor=request.user)

        initial_qs = qs.filter(appointment_type='initial')
        follow_qs = qs.filter(appointment_type='follow_up')

        initial_data = self.get_serializer(initial_qs, many=True).data
        follow_data = self.get_serializer(follow_qs, many=True).data

        return Response({
            'initial': initial_data,
            'follow_up': follow_data,
        })

    # 👩‍⚕️ Doctor can view their own today's appointments (grouped)
    @action(detail=False, methods=['get'], permission_classes=[IsDoctor])
    def today(self, request):
        today = timezone.now().date()
        doctor = request.user
        qs = Appointment.objects.filter(
            doctor=doctor,
            appointment_date__date=today
        ).order_by('appointment_date')

        initial_qs = qs.filter(appointment_type='initial')
        follow_qs = qs.filter(appointment_type='follow_up')

        initial_data = self.get_serializer(initial_qs, many=True).data
        follow_data = self.get_serializer(follow_qs, many=True).data

        return Response({
            'initial': initial_data,
            'follow_up': follow_data,
        })
