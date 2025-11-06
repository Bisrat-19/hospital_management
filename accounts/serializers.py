from rest_framework import serializers
from .models import User
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'role']

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password', 'role']

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            email=validated_data.get('email', ''),
            role=validated_data['role'],
        )
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if password:
            instance.set_password(password)
            instance.save()

        return instance

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(username=data['username'], password=data['password'])
        if user and user.is_active:
            self.user = user
            refresh = RefreshToken.for_user(user)
            self.tokens = {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
            return {'user': user}
        raise serializers.ValidationError("Invalid credentials")

    def get_token_data(self):
        user_data = UserSerializer(self.user).data if hasattr(self, 'user') else None
        return {
            'refresh': self.tokens.get('refresh') if hasattr(self, 'tokens') else None,
            'access': self.tokens.get('access') if hasattr(self, 'tokens') else None,
            'user': user_data,
        }
