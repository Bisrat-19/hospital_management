from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import permissions, status
from django.shortcuts import get_object_or_404
from ..models import User
from ..serializers import UserSerializer, RegisterSerializer



@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def list_users_view(request):
    users = User.objects.all()
    serializer = UserSerializer(users, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def get_user_view(request, pk):
    user = get_object_or_404(User, pk=pk)
    serializer = UserSerializer(user)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['PUT'])
@permission_classes([permissions.IsAdminUser])
def update_user_view(request, pk):
    user = get_object_or_404(User, pk=pk)
    serializer = RegisterSerializer(instance=user, data=request.data, partial=True)  # partial=True allows partial updates

    if serializer.is_valid():
        serializer.save()  # Save non-password fields

        # Handle password separately
        if 'password' in request.data:
            user.set_password(request.data['password'])  # Hash password
            user.save()

        return Response(UserSerializer(user).data, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([permissions.IsAdminUser])
def delete_user_view(request, pk):
    user = get_object_or_404(User, pk=pk)
    user.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)
