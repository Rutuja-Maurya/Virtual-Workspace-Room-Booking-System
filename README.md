# Virtual-Workspace-Room-Booking-System

A Django + DRF + PostgreSQL + Docker system for booking virtual workspace rooms (private, conference, shared desks) with business rules for time slots, team size, shared desk capacity, and double-booking prevention.

---

## Features

- User registration & login (token-based)
- Book/cancel/view rooms (private, conference, shared desk)
- Team management for conference rooms
- Shared desk capacity enforcement
- Double-booking prevention
- Admin dashboard
- Fully dockerized for easy setup
- **User-friendly web UI for booking, viewing, and cancelling rooms, and team management**

---

## User Interface (UI)

This project includes a modern, user-friendly web UI built with HTML, CSS, and JavaScript templates. The UI allows users to:
- Register and log in
- Book rooms (private, conference, shared desk)
- View all available and booked rooms
- Cancel bookings
- Create and manage teams (for conference rooms)
- Access a dashboard for easy navigation

All UI pages are accessible via your browser at [http://localhost:8000/](http://localhost:8000/) after starting the project.

---

##  Dockerized Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Rutuja-Maurya/Virtual-Workspace-Room-Booking-System.git
   cd Virtual-Workspace-Room-Booking-System
   ```

2. **Build and start the containers:**
   ```bash
   docker-compose up --build
   ```

3. **Create the database (if not auto-created):**
   ```bash
   docker exec -it virtual-workspace-room-booking-system-db-1 psql -U postgres -c "CREATE DATABASE virtual_workspace_db;"
   ```

4. **Run migrations:**
   ```bash
   docker exec -it virtual-workspace-room-booking-system-web-1 python manage.py makemigrations booking
   docker exec -it virtual-workspace-room-booking-system-web-1 python manage.py migrate
   ```

5. **Create a superuser (for Django admin):**
   ```bash
   docker exec -it virtual-workspace-room-booking-system-web-1 python manage.py createsuperuser
   ```
   - Example credentials:
     - **Username:** root
     - **Email:** mauryarutuja@gmail.com
     - **Password:** rutuja@07

6. **Access the app:**
   - Frontend: [http://localhost:8000/](http://localhost:8000/)
   - Admin: [http://localhost:8000/admin/](http://localhost:8000/admin/)

---

##  Running Tests

To run all tests for the booking app:

```bash
docker exec -it virtual-workspace-room-booking-system-web-1 python manage.py test booking
```

You'll see human-readable descriptions for each test in the output.

---

## Table Schemas (Models Overview)

### **User** (Django built-in)
- `username`, `password`, `email`, etc.

### **UserProfile**
- `user` (OneToOne to User)
- `age` (int)
- `gender` (str)

### **Team**
- `name` (str)
- `members` (ManyToMany to User)

### **Room**
- `name` (str, unique)
- `room_type` (private | conference | shared)
- `capacity` (int)

### **Booking**
- `room` (FK to Room)
- `user` (FK to User, nullable)
- `team` (FK to Team, nullable)
- `date` (date)
- `hour` (int, 9-18)
- `booking_id` (str, unique)
- `created_at` (datetime)

**Business rules are enforced in the model and API logic.**

---

##  Useful Commands

- **Run migrations:**  
  `docker exec -it virtual-workspace-room-booking-system-web-1 python manage.py migrate`

- **Create superuser:**  
  `docker exec -it virtual-workspace-room-booking-system-web-1 python manage.py createsuperuser`

- **Run tests:**  
  `docker exec -it virtual-workspace-room-booking-system-web-1 python manage.py test booking`

- **Access Django admin:**  
  [http://localhost:8000/admin/](http://localhost:8000/admin/)  
  (Login as `root` / `rutuja@07` or your created superuser)

---

##  API Endpoints (Key)

- `POST /api/v1/register/` — Register user
- `POST /api/v1/login/` — Login (get token)
- `GET /api/v1/rooms/available/` — List available rooms
- `POST /api/v1/bookings/` — Book a room
- `POST /api/v1/cancel/<booking_id>/` — Cancel a booking
- `GET /api/v1/bookings/` — List bookings
- `POST /api/v1/teams/create/` — Create a team

---

**For any issues, check your Docker logs!**

---

## Assumptions Made

- Users must register and log in to access booking features.
- Private rooms can only be booked by individual users (not teams).
- Conference rooms can only be booked by teams with at least 3 members.
- Shared desks can be booked by individuals, up to the room's capacity per time slot.
- A user or team cannot have more than one booking for the same time slot.
- All bookings are for one-hour slots between 9AM and 6PM (hour values 9-18).
- Only the user who made a booking can cancel it.
- Team creation requires at least 3 valid, registered users.
- The admin user is created manually via `createsuperuser`.

---

## API Documentation & Usage Samples

### Register a User
**POST** `/api/v1/register/`

**Request:**
```json
{
  "username": "alice",
  "password": "alicepass",
  "age": 25,
  "gender": "female"
}
```
**Response:**
```json
{
  "user": {"id": 1, "user": "alice", "age": 25, "gender": "female"},
  "token": "<auth_token>"
}
```

---

### Login
**POST** `/api/v1/login/`

**Request:**
```json
{
  "username": "alice",
  "password": "alicepass"
}
```
**Response:**
```json
{
  "token": "<auth_token>",
  "user": {"id": 1, "user": "alice", "age": 25, "gender": "female"}
}
```

---

### List Available Rooms
**GET** `/api/v1/rooms/available/?type=shared&date=2025-07-01&hour=10`

**Response:**
```json
{
  "rooms": [
    {"id": 2, "name": "Shared1", "type": "shared", "capacity": 4, "available_spots": 2}
  ]
}
```

---

### Book a Room
**POST** `/api/v1/bookings/` (Auth required)

**Request (private room):**
```json
{
  "room_id": 1,
  "date": "2025-07-01",
  "hour": 10
}
```
**Request (conference room):**
```json
{
  "room_id": 3,
  "date": "2025-07-01",
  "hour": 11,
  "team_id": 1
}
```
**Response:**
```json
{
  "booking_id": "...",
  "user": "alice",
  "room": "Private1",
  "type": "private",
  "date": "2025-07-01",
  "hour": 10,
  "team_id": "",
  "team_name": ""
}
```

---

### Cancel a Booking
**POST** `/api/v1/cancel/<booking_id>/` (Auth required)

**Response:**
```json
{
  "detail": "Booking cancelled successfully!"
}
```

---

### List Bookings
**GET** `/api/v1/bookings/` (Auth required)

**Response:**
```json
[
  {
    "booking_id": "...",
    "user": "alice",
    "room": "Private1",
    "type": "private",
    "date": "2025-07-01",
    "hour": 10,
    "team_id": "",
    "team_name": ""
  }
]
```

---

### Create a Team
**POST** `/api/v1/teams/create/` (Auth required)

**Request:**
```json
{
  "name": "TeamA",
  "members": ["alice", "bob", "carol"]
}
```
**Response:**
```json
{
  "id": 1,
  "name": "TeamA",
  "members": ["alice", "bob", "carol"]
}
```

---