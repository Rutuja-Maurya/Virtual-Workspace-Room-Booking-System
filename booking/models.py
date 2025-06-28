from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User as AuthUser

# User, Team, Room, and Booking models for the booking system
class UserProfile(models.Model):
    user = models.OneToOneField(AuthUser, on_delete=models.CASCADE)
    age = models.PositiveIntegerField()
    gender = models.CharField(max_length=10)
    # Add other fields as needed

    def __str__(self):
        return f"{self.user.username} Profile"

class Team(models.Model):
    name = models.CharField(max_length=100)
    members = models.ManyToManyField(AuthUser, related_name='teams')

class Room(models.Model):
    ROOM_TYPE_CHOICES = [
        ('private', 'Private'),
        ('conference', 'Conference'),
        ('shared', 'Shared Desk'),
    ]
    room_type = models.CharField(max_length=20, choices=ROOM_TYPE_CHOICES)
    capacity = models.PositiveIntegerField()
    name = models.CharField(max_length=50, unique=True)

class Booking(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    user = models.ForeignKey(AuthUser, null=True, blank=True, on_delete=models.SET_NULL)
    team = models.ForeignKey(Team, null=True, blank=True, on_delete=models.SET_NULL)
    date = models.DateField()  # Booking date
    hour = models.PositiveIntegerField()  # 9-18 (for 9AM-6PM)
    created_at = models.DateTimeField(auto_now_add=True)
    booking_id = models.CharField(max_length=100, unique=True)

    class Meta:
        pass  # No constraints here; all logic in clean()

    def clean(self):
        # Only one of user or team should be set
        if self.user and self.team:
            raise ValidationError('Booking can only have either a user or a team, not both.')
        if not self.user and not self.team:
            raise ValidationError('Booking must have either a user or a team.')
        # Enforce shared desk capacity in logic (not DB)
        if self.room.room_type == 'shared':
            count = Booking.objects.filter(
                room=self.room, date=self.date, hour=self.hour
            )
            if self.pk:
                count = count.exclude(pk=self.pk)
            if count.count() >= self.room.capacity:
                raise ValidationError('Shared desk is full for this slot.')
        # Enforce uniqueness for private/conference rooms
        if self.room.room_type in ['private', 'conference']:
            exists = Booking.objects.filter(
                room=self.room, date=self.date, hour=self.hour
            )
            if self.pk:
                exists = exists.exclude(pk=self.pk)
            if exists.exists():
                raise ValidationError('This room is already booked for the selected slot.')

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
