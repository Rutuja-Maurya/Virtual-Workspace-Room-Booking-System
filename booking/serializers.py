from rest_framework import serializers
from .models import Team, Room, Booking, UserProfile
from django.contrib.auth.models import User as AuthUser
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuthUser
        fields = ['id', 'username', 'first_name', 'last_name', 'email']

class UserProfileSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    class Meta:
        model = UserProfile
        fields = ['id', 'user', 'age', 'gender']

class UserRegistrationSerializer(serializers.ModelSerializer):
    age = serializers.IntegerField(write_only=True)
    gender = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True)

    class Meta:
        model = AuthUser
        fields = ['username', 'password', 'age', 'gender']

    def create(self, validated_data):
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

class TeamSerializer(serializers.ModelSerializer):
    members = UserSerializer(many=True, read_only=True)
    member_ids = serializers.PrimaryKeyRelatedField(
        queryset=AuthUser.objects.all(), many=True, write_only=True, source='members'
    )

    class Meta:
        model = Team
        fields = ['id', 'name', 'members', 'member_ids']

class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = ['id', 'name', 'room_type', 'capacity']

class BookingSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    team = TeamSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=AuthUser.objects.all(), write_only=True, required=False, allow_null=True, source='user'
    )
    team_id = serializers.PrimaryKeyRelatedField(
        queryset=Team.objects.all(), write_only=True, required=False, allow_null=True, source='team'
    )
    room = RoomSerializer(read_only=True)
    room_id = serializers.PrimaryKeyRelatedField(
        queryset=Room.objects.all(), write_only=True, source='room'
    )

    class Meta:
        model = Booking
        fields = [
            'id', 'room', 'room_id', 'user', 'user_id', 'team', 'team_id',
            'date', 'hour', 'booking_id', 'created_at'
        ] 