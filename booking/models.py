from django.db import models

# User, Team, Room, and Booking models for the booking system
class User(models.Model):
    name = models.CharField(max_length=100)
    age = models.PositiveIntegerField()
    gender = models.CharField(max_length=10)

class Team(models.Model):
    name = models.CharField(max_length=100)
    members = models.ManyToManyField(User, related_name='teams')

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
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    team = models.ForeignKey(Team, null=True, blank=True, on_delete=models.SET_NULL)
    slot = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    booking_id = models.CharField(max_length=100, unique=True)

    class Meta:
        unique_together = ('room', 'slot')
