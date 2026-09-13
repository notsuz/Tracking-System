from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from .models import User
from .validators import StrongPasswordValidator


# ==================== READ SERIALIZERS ====================

class UserSerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    initials = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'role_display', 'phone', 'date_of_joining',
            'is_active', 'is_superuser', 'is_staff',
            'must_change_password', 'display_name', 'initials',
        )
        read_only_fields = ('id', 'must_change_password', 'is_superuser', 'is_staff')


# ==================== AUTH SERIALIZERS ====================

class LoginSerializer(serializers.Serializer):
    """Accepts username OR email in the 'username' field."""
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs):
        login_value = attrs.get('username', '').strip()
        password = attrs.get('password', '')

        if not login_value or not password:
            raise serializers.ValidationError("Username and password are required.")

        user = authenticate(
            request=self.context.get('request'),
            username=login_value,
            password=password
        )

        if user is None:
            try:
                user_obj = User.objects.get(email__iexact=login_value)
                user = authenticate(
                    request=self.context.get('request'),
                    username=user_obj.username,
                    password=password
                )
            except User.DoesNotExist:
                user = None

        if user is None:
            raise serializers.ValidationError("Invalid credentials.")
        if not user.is_active:
            raise serializers.ValidationError("Your account has been disabled.")

        attrs['user'] = user
        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True)
    confirm_password = serializers.CharField(required=True, write_only=True)

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate(self, attrs):
        new_pw = attrs.get('new_password')
        confirm_pw = attrs.get('confirm_password')

        if new_pw != confirm_pw:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})

        if attrs.get('old_password') == new_pw:
            raise serializers.ValidationError(
                {"new_password": "New password must be different from current password."}
            )

        try:
            StrongPasswordValidator().validate(new_pw)
            validate_password(new_pw, self.context['request'].user)
        except DjangoValidationError as e:
            raise serializers.ValidationError({"new_password": list(e.messages)})

        return attrs

    def save(self, **kwargs):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.must_change_password = False
        user.save()
        return user


# ==================== ADMIN SERIALIZERS ====================

class CreateUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name',
                  'role', 'phone', 'date_of_joining', 'password')

    def validate_username(self, value):
        value = value.strip()
        if len(value) < 3:
            raise serializers.ValidationError("Username must be at least 3 characters.")
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("This username is already taken.")
        return value

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("This email is already registered.")
        return value

    def validate_password(self, value):
        try:
            StrongPasswordValidator().validate(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value

    def validate_role(self, value):
        if value not in ['intern', 'team_lead', 'admin']:
            raise serializers.ValidationError("Invalid role.")
        return value

    def create(self, validated_data):
        password = validated_data.pop('password')
        validated_data['must_change_password'] = True
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class AdminResetPasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(required=True, write_only=True)

    def validate_new_password(self, value):
        try:
            StrongPasswordValidator().validate(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value

    def save(self, **kwargs):
        user = self.context['target_user']
        user.set_password(self.validated_data['new_password'])
        user.must_change_password = True
        user.save()
        return user


class AdminUpdateUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'phone',
                  'role', 'is_active', 'date_of_joining')

    def validate_email(self, value):
        user = self.instance
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exclude(pk=user.pk).exists():
            raise serializers.ValidationError("This email is already registered.")
        return value

    def validate_role(self, value):
        if value not in ['intern', 'team_lead', 'admin']:
            raise serializers.ValidationError("Invalid role.")
        return value