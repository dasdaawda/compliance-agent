from rest_framework import serializers
from users.models import User, UserRole


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model."""
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'company_name', 'balance_minutes',
            'is_active_operator', 'performance_metric', 'date_joined'
        ]
        read_only_fields = ['id', 'date_joined', 'performance_metric']
    
    def validate_email(self, value):
        """Ensure email is lowercase and unique."""
        value = value.lower()
        if self.instance and self.instance.email == value:
            return value
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("User with this email already exists.")
        return value


class UserCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new users."""
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'password', 'first_name', 'last_name',
            'role', 'company_name', 'balance_minutes'
        ]
        read_only_fields = ['id']
    
    def validate_email(self, value):
        """Ensure email is lowercase and unique."""
        value = value.lower()
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("User with this email already exists.")
        return value
    
    def create(self, validated_data):
        """Create user with hashed password."""
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile (limited fields for non-admin users)."""
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role', 'company_name']
        read_only_fields = ['id', 'role']
