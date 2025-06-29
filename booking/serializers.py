from rest_framework import serializers
from .models import Team, Room, Booking, UserProfile
from django.contrib.auth.models import User as AuthUser
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password

# Serializer for Django's built-in User model
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuthUser
        fields = ['id', 'username', 'first_name', 'last_name', 'email']

# Serializer for UserProfile model
class UserProfileSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    class Meta:
        model = UserProfile
        fields = ['id', 'user', 'age', 'gender']

# Serializer for user registration (creates both User and UserProfile)
class UserRegistrationSerializer(serializers.ModelSerializer):
    age = serializers.IntegerField(write_only=True)
    gender = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True)

    class Meta:
        model = AuthUser
        fields = ['username', 'password', 'age', 'gender']

    def create(self, validated_data):
        # Extract extra fields and create user and profile
        age = validated_data.pop('age')
        gender = validated_data.pop('gender')
        password = validated_data.pop('password')
        user = AuthUser.objects.create(
            username=validated_data['username'],
        )
        user.set_password(password)
        user.save()
        UserProfile.objects.create(user=user, age=age, gender=gender)
        return user

# Serializer for Team model
class TeamSerializer(serializers.ModelSerializer):
    members = UserSerializer(many=True, read_only=True)
    member_ids = serializers.PrimaryKeyRelatedField(
        queryset=AuthUser.objects.all(), many=True, write_only=True, source='members'
    )

    class Meta:
        model = Team
        fields = ['id', 'name', 'members', 'member_ids']

# Serializer for Room model
class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = ['id', 'name', 'room_type', 'capacity']

# Serializer for Booking model, includes extra info fields
class BookingSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()  # Returns username
    room = serializers.SerializerMethodField()  # Returns room name
    type = serializers.SerializerMethodField()  # Returns room type
    team_id = serializers.SerializerMethodField()  # Returns team id
    team_name = serializers.SerializerMethodField()  # Returns team name

    class Meta:
        model = Booking
        fields = ['booking_id', 'user', 'room', 'type', 'date', 'hour', 'team_id', 'team_name']

    def get_user(self, obj):
        # Return username if user exists
        return obj.user.username if obj.user else ""

    def get_room(self, obj):
        # Return room name if room exists
        return obj.room.name if obj.room else ""

    def get_type(self, obj):
        # Return room type if room exists
        return obj.room.room_type if obj.room else ""

    def get_team_id(self, obj):
        # Return team id if team exists
        return obj.team.id if obj.team else ""

    def get_team_name(self, obj):
        # Return team name if team exists
        return obj.team.name if obj.team else "" 