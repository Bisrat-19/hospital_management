from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status, permissions
from django.shortcuts import get_object_or_404

from .models import Patient
from .serializers import PatientSerializer
from accounts.models import User

# Custom permission
class IsReceptionist(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'receptionist'

# Register patient (only receptionist)
@api_view(['POST'])
@permission_classes([IsReceptionist])
def register_patient_view(request):
    serializer = PatientSerializer(data=request.data)
    if serializer.is_valid():
        patient = serializer.save()
        return Response(PatientSerializer(patient).data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# List all patients
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def list_patients_view(request):
    if request.user.role in ['admin', 'receptionist']:
        patients = Patient.objects.all().order_by('-created_at')
        serializer = PatientSerializer(patients, many=True)
        return Response(serializer.data)
    return Response({'detail': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)

# Get single patient
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_patient_view(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    if request.user.role in ['admin', 'receptionist', 'doctor']:
        serializer = PatientSerializer(patient)
        return Response(serializer.data)
    return Response({'detail': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)

# Update patient (only receptionist)
@api_view(['PUT'])
@permission_classes([IsReceptionist])
def update_patient_view(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    serializer = PatientSerializer(instance=patient, data=request.data, partial=False)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Delete patient (only admin)
@api_view(['DELETE'])
@permission_classes([permissions.IsAdminUser])
def delete_patient_view(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    patient.delete()
    return Response({'message': 'Patient record deleted successfully.'}, status=status.HTTP_204_NO_CONTENT)
