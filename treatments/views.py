from rest_framework import viewsets, permissions
from .models import Treatment
from .serializers import TreatmentSerializer

class IsDoctor(permissions.BasePermission):
    """
    Allow only users with role='doctor' to create or modify treatments.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return hasattr(request.user, 'role') and request.user.role == 'doctor'


class TreatmentViewSet(viewsets.ModelViewSet):
    queryset = Treatment.objects.select_related('patient', 'doctor', 'appointment').all()
    serializer_class = TreatmentSerializer
    permission_classes = [permissions.IsAuthenticated, IsDoctor]

    def perform_create(self, serializer):
        # Automatically assign the logged-in doctor
        serializer.save(doctor=self.request.user)
