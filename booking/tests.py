from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth.models import User
from .models import Room, Team, Booking, UserProfile

# Create your tests here.

# Tests for user registration and login APIs
class UserAuthTests(APITestCase):
    def test_registration(self):
        print("\nTest: User registration should return a token and create a profile.")
        # Test the registration endpoint
        url = reverse('register')
        data = {
            'username': 'testuser',
            'password': 'testpass123',
            'age': 25,
            'gender': 'female'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('token', response.data)

    def test_login(self):
        print("\nTest: User login should return a token for valid credentials.")
        # Test the login endpoint
        user = User.objects.create_user(username='testuser2', password='testpass123')
        UserProfile.objects.create(user=user, age=30, gender='male')
        url = reverse('login')
        data = {'username': 'testuser2', 'password': 'testpass123'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)

# Tests for room booking, cancellation, and related APIs
class RoomBookingTests(APITestCase):
    def setUp(self):
        # Set up users, rooms, and teams for all tests
        self.user = User.objects.create_user(username='booker', password='pass123')
        UserProfile.objects.create(user=self.user, age=28, gender='female')
        self.private_room = Room.objects.create(name='Private1', room_type='private', capacity=1)
        self.shared_room = Room.objects.create(name='Shared1', room_type='shared', capacity=4)
        self.conference_room = Room.objects.create(name='Conf1', room_type='conference', capacity=10)
        self.team = Team.objects.create(name='TeamA')
        self.team.members.add(self.user)
        # Add extra users for team and shared desk tests
        self.user2 = User.objects.create_user(username='member2', password='pass123')
        self.user3 = User.objects.create_user(username='member3', password='pass123')
        self.user4 = User.objects.create_user(username='member4', password='pass123')  # For extra shared desk tests
        self.user5 = User.objects.create_user(username='member5', password='pass123')  # For extra shared desk tests
        self.team.members.add(self.user2, self.user3)

    def authenticate(self):
        # Helper to log in as the main user and set the token for requests
        url = reverse('login')
        data = {'username': 'booker', 'password': 'pass123'}
        response = self.client.post(url, data)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + response.data['token'])

    def test_book_private_room(self):
        print("\nTest: Booking a private room as an individual should succeed.")
        # Book a private room for the user
        self.authenticate()
        url = reverse('booking-list')
        data = {'room_id': self.private_room.id, 'date': '2025-07-01', 'hour': 10}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_book_conference_room_with_team(self):
        print("\nTest: Booking a conference room with a team of 3+ members should succeed.")
        # Book a conference room for a team with 3+ members
        self.authenticate()
        url = reverse('booking-list')
        data = {'room_id': self.conference_room.id, 'date': '2025-07-01', 'hour': 11, 'team_id': self.team.id}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_book_shared_desk(self):
        print("\nTest: Booking a shared desk as an individual should succeed if not full.")
        # Book a shared desk for the user
        self.authenticate()
        url = reverse('booking-list')
        data = {'room_id': self.shared_room.id, 'date': '2025-07-01', 'hour': 12}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_double_booking_prevention(self):
        print("\nTest: Double booking the same room and slot should fail.")
        # Try to book the same private room and slot twice
        self.authenticate()
        url = reverse('booking-list')
        data = {'room_id': self.private_room.id, 'date': '2025-07-01', 'hour': 13}
        self.client.post(url, data)
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_shared_desk_capacity(self):
        print("\nTest: Booking a shared desk up to its capacity should succeed, but the next should fail.")
        # Book a shared desk up to its capacity, then ensure the next booking fails
        self.authenticate()
        url = reverse('booking-list')
        data = {'room_id': self.shared_room.id, 'date': '2025-07-01', 'hour': 14}
        for i in range(4):
            user = User.objects.create_user(username=f'shared{i}', password='pass123')
            UserProfile.objects.create(user=user, age=20+i, gender='other')
            login = self.client.post(reverse('login'), {'username': f'shared{i}', 'password': 'pass123'})
            self.client.credentials(HTTP_AUTHORIZATION='Token ' + login.data['token'])
            resp = self.client.post(url, data)
            if resp.status_code != status.HTTP_201_CREATED:
                print(f"Booking {i} failed:", resp.data)
            self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        # 5th booking should fail
        user = User.objects.create_user(username='shared5', password='pass123')
        UserProfile.objects.create(user=user, age=30, gender='other')
        login = self.client.post(reverse('login'), {'username': 'shared5', 'password': 'pass123'})
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + login.data['token'])
        resp = self.client.post(url, data)
        print("5th booking response:", resp.data)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cancel_booking(self):
        print("\nTest: Cancelling a booking should free up the slot for others.")
        # Book and then cancel a booking, then ensure the slot is available again
        self.authenticate()
        url = reverse('booking-list')
        data = {'room_id': self.private_room.id, 'date': '2025-07-02', 'hour': 10}
        response = self.client.post(url, data)
        booking_id = response.data['booking_id']
        cancel_url = reverse('cancel-booking', args=[booking_id])
        cancel_resp = self.client.post(cancel_url)
        self.assertEqual(cancel_resp.status_code, status.HTTP_200_OK)
        # Slot should now be available
        response2 = self.client.post(url, data)
        self.assertEqual(response2.status_code, status.HTTP_201_CREATED)

    def test_list_bookings(self):
        print("\nTest: Listing bookings should show all bookings for the user.")
        # Book a room and then list bookings for the user
        self.authenticate()
        url = reverse('booking-list')
        data = {'room_id': self.private_room.id, 'date': '2025-07-03', 'hour': 10}
        self.client.post(url, data)
        list_resp = self.client.get(url)
        self.assertEqual(list_resp.status_code, status.HTTP_200_OK)
        self.assertTrue(len(list_resp.data) > 0)

    def test_room_availability(self):
        print("\nTest: The available rooms API should show correct availability for a given slot.")
        # Check available rooms for a specific slot
        url = reverse('available-rooms')
        response = self.client.get(url, {'type': 'private', 'date': '2025-07-04', 'hour': 10})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('rooms', response.data)

    def test_create_team(self):
        print("\nTest: Creating a team with 3+ members should succeed.")
        # Create a team with 3+ members
        self.authenticate()
        url = reverse('create_team')
        usernames = ['booker', 'member2', 'member3']
        data = {'name': 'TeamB', 'members': usernames}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertIn('id', response.data)
