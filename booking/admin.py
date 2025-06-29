from django.contrib import admin
from .models import Team, Room, Booking, UserProfile

admin.site.register(Team)
admin.site.register(Room)
admin.site.register(Booking)
admin.site.register(UserProfile)