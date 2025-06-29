from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User as AuthUser
from django.db import transaction
from django.db.models import Q
import uuid

# User, Team, Room, and Booking models for the booking system
# UserProfile extends the built-in User with extra fields
class UserProfile(models.Model):
    user = models.OneToOneField(AuthUser, on_delete=models.CASCADE)  # Link to Django User
    age = models.PositiveIntegerField()  # User's age
    gender = models.CharField(max_length=10)  # User's gender
    # Add other fields as needed

    def __str__(self):
        return f"{self.user.username} Profile"

# Team model for conference room bookings
class Team(models.Model):
    name = models.CharField(max_length=100)  # Team name
    members = models.ManyToManyField(AuthUser, related_name='teams')  # Team members

# Room model for all room types
class Room(models.Model):
    ROOM_TYPE_CHOICES = [
        ('private', 'Private'),
        ('conference', 'Conference'),
        ('shared', 'Shared Desk'),
    ]
    room_type = models.CharField(max_length=20, choices=ROOM_TYPE_CHOICES)  # Type of room
    capacity = models.PositiveIntegerField()  # Capacity (used for shared desks)
    name = models.CharField(max_length=50, unique=True)  # Room name

# Booking model for all bookings
class Booking(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE)  # Booked room
    user = models.ForeignKey(AuthUser, null=True, blank=True, on_delete=models.SET_NULL)  # User (for private/shared)
    team = models.ForeignKey(Team, null=True, blank=True, on_delete=models.SET_NULL)  # Team (for conference)
    date = models.DateField()  # Booking date
    hour = models.PositiveIntegerField()  # 9-18 (for 9AM-6PM)
    created_at = models.DateTimeField(auto_now_add=True)  # Timestamp
    booking_id = models.CharField(max_length=100, unique=True)  # Unique booking identifier

    class Meta:
        # Remove unique_together, rely on clean() for logic
        indexes = [
            models.Index(fields=['room', 'date', 'hour']),
            models.Index(fields=['user', 'date', 'hour']),
            models.Index(fields=['team', 'date', 'hour']),
        ]

    def clean(self):
        # Only one of user or team should be set
        if self.user and self.team:
            raise ValidationError('Booking can only have either a user or a team, not both.')
        if not self.user and not self.team:
            raise ValidationError('Booking must have either a user or a team.')
        # Validate hour range
        if self.hour < 9 or self.hour > 18:
            raise ValidationError('Booking hours must be between 9 and 18 (9AM-6PM).')
        if self.room.room_type == 'shared':
            # Allow up to capacity
            count = Booking.objects.filter(room=self.room, date=self.date, hour=self.hour)
            if self.pk:
                count = count.exclude(pk=self.pk)
            if count.count() >= self.room.capacity:
                raise ValidationError('Shared desk is full for this slot.')
        else:
            # For private/conference, enforce uniqueness
            exists = Booking.objects.filter(room=self.room, date=self.date, hour=self.hour)
            if self.pk:
                exists = exists.exclude(pk=self.pk)
            if exists.exists():
                raise ValidationError('This room is already booked for the selected slot.')

    def save(self, *args, **kwargs):
        # Validate before saving
        self.full_clean()
        super().save(*args, **kwargs)

    @classmethod
    def create_booking_with_lock(cls, room, user=None, team=None, date=None, hour=None):
        """
        Create a booking with proper locking to prevent race conditions.
        This method uses database-level locking to ensure atomicity.
        """
        if not room or not date or not hour:
            raise ValueError("Room, date, and hour are required.")
        if not user and not team:
            raise ValueError("Either user or team must be provided.")
        if user and team:
            raise ValueError("Cannot specify both user and team.")
        # Lock existing bookings for this room and slot
        with transaction.atomic():
            existing_bookings = cls.objects.select_for_update().filter(
                room=room, date=date, hour=hour
            )
            # Check if slot is available
            if room.room_type in ['private', 'conference']:
                if existing_bookings.exists():
                    raise ValidationError('This room is already booked for the selected slot.')
            elif room.room_type == 'shared':
                if existing_bookings.count() >= room.capacity:
                    raise ValidationError('Shared desk is full for this slot.')
            # Check for user/team double booking
            if user:
                user_bookings = cls.objects.select_for_update().filter(
                    user=user, date=date, hour=hour
                )
                if user_bookings.exists():
                    raise ValidationError('You already have a booking for this slot.')
            elif team:
                team_bookings = cls.objects.select_for_update().filter(
                    team=team, date=date, hour=hour
                )
                if team_bookings.exists():
                    raise ValidationError('Your team already has a booking for this slot.')
            # Create and save the booking
            booking = cls(
                room=room,
                user=user,
                team=team,
                date=date,
                hour=hour,
                booking_id=str(uuid.uuid4())
            )
            booking.save()
            return booking

    @classmethod
    def check_availability(cls, room, date, hour):
        """
        Check if a room is available for a specific slot.
        This method uses proper locking to ensure accurate results.
        """
        with transaction.atomic():
            existing_bookings = cls.objects.select_for_update().filter(
                room=room, date=date, hour=hour
            )
            if room.room_type in ['private', 'conference']:
                return not existing_bookings.exists()
            elif room.room_type == 'shared':
                return existing_bookings.count() < room.capacity
            return False
