from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from .models import Booking, Room, Team, UserProfile
from .serializers import BookingSerializer, UserSerializer, UserRegistrationSerializer, UserProfileSerializer
from django.db import transaction
from django.utils import timezone
import uuid
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.core.exceptions import ValidationError
from rest_framework.decorators import api_view, permission_classes

# Create your views here.

# RegisterView handles user registration and token creation
@method_decorator(csrf_exempt, name='dispatch')
class RegisterView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        # Validate and create user and profile, return token
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            token, created = Token.objects.get_or_create(user=user)
            profile = UserProfile.objects.get(user=user)
            return Response({
                'user': UserProfileSerializer(profile).data,
                'token': token.key
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# LoginView handles user authentication and returns token and profile
@method_decorator(csrf_exempt, name='dispatch')
class LoginView(ObtainAuthToken):
    permission_classes = [AllowAny]
    def post(self, request, *args, **kwargs):
        # Authenticate user and return token and profile
        response = super().post(request, *args, **kwargs)
        token = Token.objects.get(key=response.data['token'])
        user = token.user
        profile = UserProfile.objects.get(user=user)
        return Response({
            'token': token.key,
            'user': UserProfileSerializer(profile).data
        })

# BookingViewSet handles booking creation, listing, and validation
class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all().order_by('-created_at')
    serializer_class = BookingSerializer

    def create(self, request, *args, **kwargs):
        # Extract and validate booking data
        data = request.data.copy()
        room_id = data.get('room_id')
        team_id = data.get('team_id')
        date = data.get('date')
        hour = data.get('hour')
        user = request.user  # Always use the authenticated user for private/shared bookings

        # Validate required fields
        if not room_id or not date or not hour:
            return Response({'detail': 'room_id, date, and hour are required.'}, status=400)

        try:
            room = Room.objects.get(id=room_id)
        except Room.DoesNotExist:
            return Response({'detail': 'Room does not exist.'}, status=404)

        # Validate hour range
        try:
            hour = int(hour)
            if hour < 9 or hour > 18:
                return Response({'detail': 'Booking hours must be between 9 and 18 (9AM-6PM).'}, status=400)
        except ValueError:
            return Response({'detail': 'Invalid hour value.'}, status=400)

        # Business rules for room types
        if room.room_type == 'private':
            # Private rooms: only individual users
            if team_id:
                return Response({'detail': 'Private rooms can only be booked by individual users.'}, status=400)
        elif room.room_type == 'conference':
            # Conference rooms: only teams with 3+ members
            if not team_id:
                return Response({'detail': 'Conference rooms can only be booked by teams.'}, status=400)
            try:
                team = Team.objects.get(id=team_id)
            except Team.DoesNotExist:
                return Response({'detail': 'Team does not exist.'}, status=404)
            members = team.members.all()
            if members.count() < 3:
                return Response({'detail': 'Conference rooms require a team of at least 3 members.'}, status=400)
        elif room.room_type == 'shared':
            # Shared desks: only individuals
            if team_id:
                return Response({'detail': 'Shared desks can only be booked by individual users.'}, status=400)

        try:
            # Use locking method to prevent race conditions
            if team_id:
                try:
                    team = Team.objects.get(id=team_id)
                except Team.DoesNotExist:
                    return Response({'detail': 'Team does not exist.'}, status=404)
                booking = Booking.create_booking_with_lock(
                    room=room,
                    team=team,
                    date=date,
                    hour=hour
                )
            else:
                booking = Booking.create_booking_with_lock(
                    room=room,
                    user=user,
                    date=date,
                    hour=hour
                )
            # Serialize and return the created booking
            serializer = self.get_serializer(booking)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        except ValidationError as e:
            return Response({'detail': str(e)}, status=400)
        except ValueError as e:
            return Response({'detail': str(e)}, status=400)
        except Exception as e:
            return Response({'detail': 'An error occurred while creating the booking.'}, status=500)

    def list(self, request, *args, **kwargs):
        # List all bookings for the user
        return super().list(request, *args, **kwargs)

# Render home page
def home(request):
    return render(request, 'home.html')

# Render dashboard page
def dashboard(request):
    return render(request, 'dashboard.html')

# AvailableRoomsView returns available rooms for a given type, date, and hour
class AvailableRoomsView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        room_type = request.GET.get('type')
        date = request.GET.get('date')
        hour = request.GET.get('hour')
        rooms = Room.objects.all()
        if room_type:
            rooms = rooms.filter(room_type=room_type)
        available_rooms = []
        # Check each room for availability
        for room in rooms:
            if date and hour:
                try:
                    hour_int = int(hour)
                    # Use locking method to check availability
                    is_available = Booking.check_availability(room, date, hour_int)
                    if is_available:
                        # For shared desks, calculate available spots
                        if room.room_type == 'shared':
                            count = Booking.objects.filter(room=room, date=date, hour=hour_int).count()
                            available_spots = room.capacity - count
                        else:
                            available_spots = 1
                        available_rooms.append({
                            'id': room.id,
                            'name': room.name,
                            'type': room.room_type,
                            'capacity': room.capacity,
                            'available_spots': available_spots
                        })
                except ValueError:
                    # Skip invalid hour values
                    continue
            else:
                available_rooms.append({
                    'id': room.id,
                    'name': room.name,
                    'type': room.room_type,
                    'capacity': room.capacity,
                    'available_spots': room.capacity if room.room_type == 'shared' else 1
                })
        # If no rooms available for the slot, return a message
        if date and hour and room_type and not available_rooms:
            return Response({
                'rooms': [],
                'message': 'No available room for the selected slot and type.'
            })
        return Response({'rooms': available_rooms})

# Render book room page
def book_room(request):
    return render(request, 'book_room.html')

# Render available rooms page
def available_rooms_page(request):
    return render(request, 'available_rooms.html')

# Render booked rooms page
def booked_rooms_page(request):
    return render(request, 'booked_rooms.html')

# Render cancel booking page
def cancel_booking_page(request):
    return render(request, 'cancel_booking.html')

# CancelBookingView handles booking cancellation and slot freeing
class CancelBookingView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, booking_id):
        user = request.user
        try:
            booking = Booking.objects.get(booking_id=booking_id)
        except Booking.DoesNotExist:
            return Response({'detail': 'Booking not found.'}, status=status.HTTP_404_NOT_FOUND)
        # Only allow if the booking was made by this user
        if booking.user != user:
            return Response({'detail': 'No booking done by you with this booking ID.'}, status=status.HTTP_403_FORBIDDEN)
        # Delete booking to free up slot
        booking.delete()
        return Response({'detail': 'Booking cancelled successfully!'}, status=status.HTTP_200_OK)

# create_team API endpoint to create a new team with members
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_team(request):
    name = request.data.get('name')
    member_usernames = request.data.get('members', [])
    if not name or not member_usernames:
        return Response({'detail': 'Team name and at least 3 members are required.'}, status=400)
    if len(member_usernames) < 3:
        return Response({'detail': 'Conference rooms require a team of at least 3 members.'}, status=400)
    from django.contrib.auth.models import User
    members = User.objects.filter(username__in=member_usernames)
    if members.count() < 3:
        return Response({'detail': 'Some users not found or less than 3 valid members.'}, status=400)
    team = Team.objects.create(name=name)
    team.members.set(members)
    team.save()
    return Response({'id': team.id, 'name': team.name, 'members': [u.username for u in members]}, status=201)

# Render create team page
def create_team_page(request):
    return render(request, 'create_team.html')
