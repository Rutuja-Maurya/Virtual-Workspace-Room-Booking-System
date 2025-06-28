"""
URL configuration for virtual_workspace project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from booking.views import BookingViewSet, RegisterView, LoginView, home, dashboard, AvailableRoomsView, book_room, available_rooms_page, booked_rooms_page, cancel_booking_page, CancelBookingView
from rest_framework.authtoken.views import obtain_auth_token

router = DefaultRouter()
router.register(r'bookings', BookingViewSet, basename='booking')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include(router.urls)),
    path('api-token-auth/', obtain_auth_token, name='api_token_auth'),
    path('api/v1/register/', RegisterView.as_view(), name='register'),
    path('api/v1/login/', LoginView.as_view(), name='login'),
    path('', home, name='home'),
    path('dashboard/', dashboard, name='dashboard'),
    path('api/v1/rooms/available/', AvailableRoomsView.as_view(), name='available-rooms'),
    path('book-room/', book_room, name='book-room'),
    path('available-rooms/', available_rooms_page, name='available-rooms-page'),
    path('booked-rooms/', booked_rooms_page, name='booked-rooms-page'),
    path('api/v1/cancel/<str:booking_id>/', CancelBookingView.as_view(), name='cancel-booking'),
    path('cancel-booking/', cancel_booking_page, name='cancel-booking-page'),
]
