from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from .models import CustomerProfile, User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "first_name", "last_name", "role", "is_active", "date_joined")
        read_only_fields = fields


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ("email", "password", "first_name", "last_name")

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        CustomerProfile.objects.create(user=user)
        return user

    def to_representation(self, instance):
        refresh = RefreshToken.for_user(instance)
        return {
            "user": UserSerializer(instance).data,
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }


class LoginSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = UserSerializer(self.user).data
        return data


class CustomerProfileSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = CustomerProfile
        fields = (
            "id",
            "user",
            "user_email",
            "phone_number",
            "address",
            "city",
            "country",
            "date_of_birth",
            "emergency_contact_name",
            "emergency_contact_phone",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "user", "user_email", "created_at", "updated_at")

    def validate_phone_number(self, value):
        return value.strip()

    def validate_emergency_contact_phone(self, value):
        return value.strip()

    def validate(self, attrs):
        for field in ("address", "city", "country", "emergency_contact_name"):
            if field in attrs and attrs[field] and not attrs[field].strip():
                raise serializers.ValidationError({field: "This field cannot contain only whitespace."})
        return attrs
