from rest_framework import serializers
from .models import User
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

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

class ChangePasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True, required=False)

    def validate(self, attrs):
        user = self.context.get('user')
        new_password = attrs.get('new_password')
        confirm_password = attrs.get('confirm_password', None)

        if not new_password:
            raise serializers.ValidationError({"new_password": "This field is required."})
        if confirm_password is not None and new_password != confirm_password:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})

        try:
            validate_password(new_password, user=user)
        except ValidationError as e:
            raise serializers.ValidationError({"new_password": list(e.messages)})
        return attrs

    def save(self, **kwargs):
        user = self.context['user']
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user
