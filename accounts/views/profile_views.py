from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import permissions
from ..serializers import UserSerializer


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def profile_view(request):
    user = request.user
    serializer = UserSerializer(user)
    return Response(serializer.data)