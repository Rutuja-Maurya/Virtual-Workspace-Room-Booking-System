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

# Create your views here.

@method_decorator(csrf_exempt, name='dispatch')
class RegisterView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
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

@method_decorator(csrf_exempt, name='dispatch')
class LoginView(ObtainAuthToken):
    permission_classes = [AllowAny]
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        token = Token.objects.get(key=response.data['token'])
        user = token.user
        profile = UserProfile.objects.get(user=user)
        return Response({
            'token': token.key,
            'user': UserProfileSerializer(profile).data
        })

class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all().order_by('-created_at')
    serializer_class = BookingSerializer

    def create(self, request, *args, **kwargs):
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

        # Booking for private room: only individual users
        if room.room_type == 'private':
            # Only allow if no team_id is provided (individual user)
            if team_id:
                return Response({'detail': 'Private rooms can only be booked by individual users.'}, status=400)
        # Booking for conference room: only teams with 3+ (excluding children for seat count)
        elif room.room_type == 'conference':
            # Only allow if team_id is provided
            if not team_id:
                return Response({'detail': 'Conference rooms can only be booked by teams.'}, status=400)
            try:
                team = Team.objects.get(id=team_id)
            except Team.DoesNotExist:
                return Response({'detail': 'Team does not exist.'}, status=404)
            members = team.members.all()
            if members.count() < 3:
                return Response({'detail': 'Conference rooms require a team of at least 3 members.'}, status=400)
        # Shared desk: only individuals, up to 4 per slot
        elif room.room_type == 'shared':
            # Only allow if no team_id is provided (individual user)
            if team_id:
                return Response({'detail': 'Shared desks can only be booked by individual users.'}, status=400)

        # Prevent double booking for user/team in the same slot (any room)
        if not team_id:
            # Check if the logged-in user already has a booking for this slot
            if Booking.objects.filter(user=user, date=date, hour=hour).exists():
                return Response({'detail': 'You already have a booking for this slot.'}, status=400)
        if team_id:
            # Check if the team already has a booking for this slot
            if Booking.objects.filter(team_id=team_id, date=date, hour=hour).exists():
                return Response({'detail': 'Your team already has a booking for this slot.'}, status=400)

        # Remove user_id from data if present (for safety)
        data.pop('user_id', None)

        # Generate unique booking_id
        data['booking_id'] = str(uuid.uuid4())

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                # For private/shared bookings, set the user before saving
                if not team_id:
                    serializer.save(user=request.user)  # Set the user field to the logged-in user
                else:
                    serializer.save()
        except Exception as e:
            return Response({'detail': str(e)}, status=400)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

def home(request):
    return render(request, 'home.html')

def dashboard(request):
    return render(request, 'dashboard.html')

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
        for room in rooms:
            if date and hour:
                # For shared desk, check capacity
                if room.room_type == 'shared':
                    count = Booking.objects.filter(room=room, date=date, hour=hour).count()
                    if count < room.capacity:
                        available_rooms.append({
                            'id': room.id,
                            'name': room.name,
                            'type': room.room_type,
                            'capacity': room.capacity
                        })
                else:
                    exists = Booking.objects.filter(room=room, date=date, hour=hour).exists()
                    if not exists:
                        available_rooms.append({
                            'id': room.id,
                            'name': room.name,
                            'type': room.room_type,
                            'capacity': room.capacity
                        })
            else:
                available_rooms.append({
                    'id': room.id,
                    'name': room.name,
                    'type': room.room_type,
                    'capacity': room.capacity
                })
        return Response({'rooms': available_rooms})

def book_room(request):
    return render(request, 'book_room.html')

def available_rooms_page(request):
    return render(request, 'available_rooms.html')

def booked_rooms_page(request):
    return render(request, 'booked_rooms.html')

def cancel_booking_page(request):
    return render(request, 'cancel_booking.html')

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
        
        booking.delete()
        return Response({'detail': 'Booking cancelled successfully!'}, status=status.HTTP_200_OK)
