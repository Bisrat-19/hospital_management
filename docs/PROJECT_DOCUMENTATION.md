# Hospital Management System - Project Documentation

## Table of Contents
1. [System Overview](#system-overview)
2. [System Architecture](#system-architecture)
3. [User Roles & Permissions](#user-roles--permissions)
4. [Complete Workflow](#complete-workflow)
5. [Apps Overview](#apps-overview)
6. [API Endpoints Reference](#api-endpoints-reference)
7. [Data Models](#data-models)
8. [Authentication & Security](#authentication--security)

---

## System Overview

This is a **Hospital Management System** built with Django REST Framework (DRF) that manages the complete patient journey from registration to treatment and follow-up appointments. The system uses a role-based access control (RBAC) model with JWT authentication and integrates with the Chapa payment gateway for processing registration fees.

### Technology Stack
- **Backend Framework**: Django 5.2.7 with Django REST Framework
- **Database**: PostgreSQL
- **Authentication**: JWT (Simple JWT)
- **Caching**: Redis with django-redis
- **Payment Gateway**: Chapa (Ethiopian payment provider)
- **API Documentation**: drf-spectacular (OpenAPI 3.0)

### Key Features
- Role-based access control (Admin, Doctor, Receptionist)
- Patient registration with automatic queue assignment
- Integrated payment processing (Cash & Chapa)
- Automatic initial appointment creation
- Doctor-patient assignment
- Treatment management with follow-up appointments
- Comprehensive caching for performance
- RESTful API design

---

## System Architecture

### Applications Structure
The project consists of **5 Django apps**:

1. **accounts** - User management and authentication
2. **patients** - Patient registration and management
3. **appointments** - Initial and follow-up appointment scheduling
4. **treatments** - Treatment records and prescriptions
5. **payments** - Payment processing (Cash & Chapa integration)

### Database Schema
- PostgreSQL with relational data model
- Foreign key relationships linking patients, appointments, treatments, and payments
- Unique constraints ensuring data integrity
- Auto-incrementing queue numbers and appointment sequences

---

## User Roles & Permissions

### 1. Admin (`admin`)
**Capabilities:**
- Create, update, and delete all users (doctors and receptionists)
- Full access to all system resources
- View all patients, appointments, treatments, and payments
- Manage user passwords
- Access admin panel

**Dashboard Features:**
- User management panel
- System-wide statistics
- Complete audit trail

**Key Responsibilities:**
- Manually create user accounts for doctors and receptionists
- Provide username and password to staff members
- Manage system configuration

### 2. Receptionist (`receptionist`)
**Capabilities:**
- Register new patients
- Collect registration fees (cash or Chapa)
- Assign doctors to patients (or auto-assign)
- View patient list
- Update patient information
- View appointment schedules

**Dashboard Features:**
- Patient registration form
- Payment collection interface
- Today's patient queue
- Doctor availability

**Key Responsibilities:**
- Greet patients upon hospital arrival
- Register patient demographic information
- Process registration payments
- Create initial appointment automatically
- Assign or auto-assign doctor to patient

### 3. Doctor (`doctor`)
**Capabilities:**
- View assigned patients
- Access patient history and appointments
- View today's appointment schedule
- Provide treatment (diagnosis, prescription)
- Create follow-up appointments when necessary
- Complete appointments

**Dashboard Features:**
- Today's appointments (initial & follow-up)
- Patient treatment history
- Treatment form (notes, prescription)
- Follow-up scheduling

**Key Responsibilities:**
- See patients in their assigned queue
- Provide medical diagnosis and treatment
- Create treatment records
- Schedule follow-up appointments if needed
- Mark appointments as completed

---

## Complete Workflow

### Patient Journey: From Registration to Follow-up

#### Step 1: Patient Arrival & Registration
1. **Patient arrives** at the hospital reception desk
2. **Receptionist** logs into their dashboard
3. **Receptionist registers patient** with the following information:
   - First name, last name
   - Date of birth
   - Gender (Male/Female)
   - Contact number
   - Address
   - Assigned doctor (optional - auto-assigns if not specified)

#### Step 2: Payment Collection
4. **Receptionist collects registration fee** through:
   - **Option A: Cash Payment** - Payment marked as "paid" immediately
   - **Option B: Chapa Payment** - Patient receives payment link, completes online payment
5. **System validates** payment before proceeding

#### Step 3: Automatic Appointment Creation
6. **System automatically creates**:
   - Queue number (auto-incremented daily)
   - Initial appointment with assigned doctor
   - Appointment type: "initial"
   - Status: "pending"

#### Step 4: Doctor Consultation
7. **Patient goes** to assigned doctor's room
8. **Doctor logs in** and sees patient in "Today's Appointments"
9. **Doctor reviews** patient information and initial appointment
10. **Doctor provides treatment**:
    - Records diagnosis notes
    - Writes prescription
    - Marks if follow-up is required

#### Step 5: Treatment Record Creation
11. **System creates treatment record** linked to:
    - Patient
    - Doctor
    - Initial appointment
12. **Treatment is unique per patient** (one treatment record per patient)

#### Step 6: Follow-up Appointment (if needed)
13. **If follow-up required**, doctor creates follow-up appointment:
    - Links to initial appointment
    - Links to treatment record
    - Sets follow-up date
    - Type: "follow_up"
14. **On follow-up day**:
    - Patient returns to hospital
    - Doctor sees patient in appointments
    - Accesses **same treatment record** (no new treatment created)
    - Updates existing treatment with new notes/prescription
15. **Multiple follow-ups** can be created, all linked to:
    - Same initial appointment
    - Same patient
    - Same treatment record

#### Step 7: Appointment Completion
16. **When treatment complete** and no follow-up needed:
    - Doctor marks appointment as "completed"
    - Patient journey ends

---

## Apps Overview

### 1. Accounts App
**Purpose**: User authentication and management

**Models:**
- `User` (extends Django's AbstractUser)
  - Fields: username, email, first_name, last_name, role, password
  - Roles: admin, doctor, receptionist

**Key Features:**
- JWT-based authentication
- Role-based permissions
- User CRUD operations (admin only)
- Password change functionality
- Redis caching for user data

### 2. Patients App
**Purpose**: Patient registration and information management

**Models:**
- `Patient`
  - Fields: first_name, last_name, date_of_birth, gender, contact_number, address
  - Relationships: assigned_doctor (ForeignKey to User)
  - Auto-fields: queue_number (daily auto-increment), is_seen, timestamps

**Key Features:**
- Automatic queue number assignment
- Doctor assignment (manual or automatic)
- Duplicate patient detection
- Integrated payment processing during registration
- Automatic initial appointment creation
- Redis caching

### 3. Appointments App
**Purpose**: Appointment scheduling and management

**Models:**
- `Appointment`
  - Types: "initial" or "follow_up"
  - Status: "pending", "completed", "cancelled"
  - Relationships: patient, doctor, initial_appointment (self-reference), treatment
  - Sequences: type_seq (unique per type), case_followup_seq (per initial appointment)

**Key Features:**
- Auto-creation of initial appointments on patient registration
- Follow-up appointment linking to initial appointment
- Follow-up appointments linked to treatment records
- Constraint validation (initial cannot have treatment, follow-up must have treatment)
- Grouped listing (initial vs follow-up)
- Doctor's "today" appointments view

### 4. Treatments App
**Purpose**: Medical treatment records and prescriptions

**Models:**
- `Treatment`
  - Fields: notes (diagnosis), prescription, follow_up_required
  - Relationships: patient, doctor, appointment (initial)
  - Constraint: Unique treatment per patient

**Key Features:**
- One treatment record per patient (persists across follow-ups)
- Linked to initial appointment
- Follow-up appointments update same treatment record
- Doctor can only manage their own treatments
- Auto-completion of appointment when follow-up not required

### 5. Payments App
**Purpose**: Payment processing and gateway integration

**Models:**
- `Payment`
  - Fields: amount, payment_method (cash/chapa), reference, status
  - Relationships: patient (ForeignKey)
  - Constraint: One successful payment per patient

**Key Features:**
- Cash payment (instant confirmation)
- Chapa integration (payment link generation)
- Webhook for payment verification
- Unique payment per patient
- Reference tracking with UUID

---

## API Endpoints Reference

### Base URL
```
http://localhost:8000
```

### Authentication Header
All authenticated endpoints require:
```
Authorization: Bearer <access_token>
```

---

### Accounts App (`/accounts/`)

#### 1. User Registration (Admin Only)
**POST** `/accounts/auth/register/`

**Permission**: Admin only

**Request:**
```json
{
  "username": "dr_john",
  "password": "SecurePass123!",
  "first_name": "John",
  "last_name": "Doe",
  "email": "john.doe@hospital.com",
  "role": "doctor"
}
```

**Response:** (201 Created)
```json
{
  "id": 5,
  "username": "dr_john",
  "first_name": "John",
  "last_name": "Doe",
  "email": "john.doe@hospital.com",
  "role": "doctor"
}
```

#### 2. Login
**POST** `/accounts/auth/login/`

**Permission**: Any (AllowAny)

**Request:**
```json
{
  "username": "dr_john",
  "password": "SecurePass123!"
}
```

**Response:** (200 OK)
```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": {
    "id": 5,
    "username": "dr_john",
    "first_name": "John",
    "last_name": "Doe",
    "email": "john.doe@hospital.com",
    "role": "doctor"
  }
}
```

#### 3. Get User Profile
**GET** `/accounts/users/profile/`

**Permission**: Authenticated

**Response:** (200 OK)
```json
{
  "id": 5,
  "username": "dr_john",
  "first_name": "John",
  "last_name": "Doe",
  "email": "john.doe@hospital.com",
  "role": "doctor"
}
```

#### 4. List All Users
**GET** `/accounts/users/`

**Permission**: Admin only

**Response:** (200 OK)
```json
[
  {
    "id": 1,
    "username": "admin",
    "first_name": "Admin",
    "last_name": "User",
    "email": "admin@hospital.com",
    "role": "admin"
  },
  {
    "id": 2,
    "username": "reception1",
    "first_name": "Sarah",
    "last_name": "Smith",
    "email": "sarah@hospital.com",
    "role": "receptionist"
  }
]
```

#### 5. Get Single User
**GET** `/accounts/users/{id}/`

**Permission**: Admin only

**Response:** (200 OK)
```json
{
  "id": 5,
  "username": "dr_john",
  "first_name": "John",
  "last_name": "Doe",
  "email": "john.doe@hospital.com",
  "role": "doctor"
}
```

#### 6. Update User
**PUT/PATCH** `/accounts/users/{id}/`

**Permission**: Admin only

**Request:**
```json
{
  "first_name": "John",
  "last_name": "Smith",
  "email": "john.smith@hospital.com"
}
```

#### 7. Change Password
**PATCH** `/accounts/users/{id}/change-password/`

**Permission**: Admin or self

**Request:**
```json
{
  "new_password": "NewSecurePass123!",
  "confirm_password": "NewSecurePass123!"
}
```

**Response:** (200 OK)
```json
{
  "detail": "Password updated successfully"
}
```

#### 8. Delete User
**DELETE** `/accounts/users/{id}/`

**Permission**: Admin only

**Response:** (204 No Content)

---

### Patients App (`/patients/`)

#### 1. Register New Patient
**POST** `/patients/`

**Permission**: Receptionist only

**Request:**
```json
{
  "first_name": "Jane",
  "last_name": "Williams",
  "date_of_birth": "1990-05-15",
  "gender": "F",
  "contact_number": "+251911234567",
  "address": "Addis Ababa, Bole",
  "assigned_doctor_id": 5,
  "payment_method": "cash",
  "amount": "500.00"
}
```

**Response:** (201 Created)
```json
{
  "id": 10,
  "first_name": "Jane",
  "last_name": "Williams",
  "date_of_birth": "1990-05-15",
  "gender": "F",
  "contact_number": "+251911234567",
  "address": "Addis Ababa, Bole",
  "assigned_doctor": {
    "id": 5,
    "username": "dr_john",
    "email": "john.doe@hospital.com"
  },
  "queue_number": 23,
  "is_seen": false,
  "created_at": "2025-12-09T14:30:00Z",
  "updated_at": "2025-12-09T14:30:00Z",
  "payment": {
    "id": 15,
    "amount": "500.00",
    "payment_method": "cash",
    "status": "paid",
    "reference": "a8b7c6d5-e4f3-g2h1-i0j9-k8l7m6n5o4p3"
  }
}
```

**For Chapa Payment:**
```json
{
  "payment_method": "chapa",
  "amount": "500.00"
}
```

**Response includes:**
```json
{
  "payment": {
    "id": 16,
    "amount": "500.00",
    "payment_method": "chapa",
    "status": "pending",
    "reference": "b9c8d7e6-f5g4-h3i2-j1k0-l9m8n7o6p5q4",
    "payment_url": "https://checkout.chapa.co/checkout/payment/..."
  }
}
```

#### 2. List All Patients
**GET** `/patients/`

**Permission**: Admin or Receptionist

**Response:** (200 OK)
```json
[
  {
    "id": 10,
    "first_name": "Jane",
    "last_name": "Williams",
    "date_of_birth": "1990-05-15",
    "gender": "F",
    "contact_number": "+251911234567",
    "address": "Addis Ababa, Bole",
    "assigned_doctor": {
      "id": 5,
      "username": "dr_john",
      "email": "john.doe@hospital.com"
    },
    "queue_number": 23,
    "is_seen": false,
    "created_at": "2025-12-09T14:30:00Z",
    "updated_at": "2025-12-09T14:30:00Z"
  }
]
```

#### 3. Get Single Patient
**GET** `/patients/{id}/`

**Permission**: Admin, Receptionist, or Doctor

**Response:** (200 OK) - Same as list item

#### 4. Update Patient
**PUT/PATCH** `/patients/{id}/`

**Permission**: Receptionist only

**Request:**
```json
{
  "contact_number": "+251922334455",
  "address": "Addis Ababa, Kirkos"
}
```

#### 5. Delete Patient
**DELETE** `/patients/{id}/`

**Permission**: Admin only

**Response:** (204 No Content)

---

### Appointments App (`/appointments/`)

#### 1. List All Appointments (Grouped)
**GET** `/appointments/`

**Permission**: Admin, Receptionist, or Doctor

**Response:** (200 OK)
```json
{
  "initial": [
    {
      "id": 50,
      "patient": 10,
      "doctor": 5,
      "appointment_date": "2025-12-09T14:30:00Z",
      "appointment_type": "initial",
      "initial_appointment": null,
      "treatment": null,
      "type_seq": 50,
      "case_followup_seq": null,
      "notes": "Initial consultation upon registration.",
      "status": "pending",
      "created_at": "2025-12-09T14:30:00Z",
      "updated_at": "2025-12-09T14:30:00Z"
    }
  ],
  "follow_up": [
    {
      "id": 51,
      "patient": 8,
      "doctor": 5,
      "appointment_date": "2025-12-15T10:00:00Z",
      "appointment_type": "follow_up",
      "initial_appointment": 45,
      "treatment": 12,
      "type_seq": 15,
      "case_followup_seq": 1,
      "notes": "Follow-up for blood pressure check",
      "status": "pending",
      "created_at": "2025-12-09T15:00:00Z",
      "updated_at": "2025-12-09T15:00:00Z"
    }
  ]
}
```

#### 2. Today's Appointments (Doctor)
**GET** `/appointments/today/`

**Permission**: Doctor only

**Response:** (200 OK) - Same grouped format, filtered for logged-in doctor and today's date

#### 3. Get Single Appointment
**GET** `/appointments/{id}/`

**Permission**: Admin, Receptionist, or Doctor

**Response:** (200 OK)
```json
{
  "id": 50,
  "patient": 10,
  "doctor": 5,
  "appointment_date": "2025-12-09T14:30:00Z",
  "appointment_type": "initial",
  "initial_appointment": null,
  "treatment": null,
  "type_seq": 50,
  "case_followup_seq": null,
  "notes": "Initial consultation upon registration.",
  "status": "pending",
  "created_at": "2025-12-09T14:30:00Z",
  "updated_at": "2025-12-09T14:30:00Z"
}
```

#### 4. Create Follow-up Appointment
**POST** `/appointments/`

**Permission**: Doctor only

**Request:**
```json
{
  "patient": 10,
  "doctor": 5,
  "appointment_date": "2025-12-15T10:00:00Z",
  "appointment_type": "follow_up",
  "initial_appointment": 50,
  "treatment": 12,
  "notes": "Follow-up for blood pressure check"
}
```

**Response:** (201 Created) - Same as GET response

#### 5. Update Appointment
**PUT/PATCH** `/appointments/{id}/`

**Permission**: Doctor only

**Request:**
```json
{
  "status": "completed",
  "notes": "Patient showed improvement"
}
```

#### 6. Delete Appointment
**DELETE** `/appointments/{id}/`

**Permission**: Admin only

**Response:** (204 No Content)

---

### Treatments App (`/treatments/`)

#### 1. Create Treatment
**POST** `/treatments/`

**Permission**: Doctor only

**Request:**
```json
{
  "appointment": 50,
  "notes": "Patient diagnosed with hypertension. Blood pressure: 140/90.",
  "prescription": "Amlodipine 5mg once daily. Low sodium diet.",
  "follow_up_required": true
}
```

**Response:** (201 Created)
```json
{
  "id": 12,
  "patient": 10,
  "doctor": 5,
  "appointment": 50,
  "notes": "Patient diagnosed with hypertension. Blood pressure: 140/90.",
  "prescription": "Amlodipine 5mg once daily. Low sodium diet.",
  "follow_up_required": true,
  "created_at": "2025-12-09T15:00:00Z"
}
```

> **Note**: The appointment field should reference the **initial appointment**. The system extracts patient and doctor from the appointment, and ensures uniqueness per patient.

#### 2. List All Treatments
**GET** `/treatments/`

**Permission**: Authenticated (Doctors see only their own)

**Response:** (200 OK)
```json
[
  {
    "id": 12,
    "patient": 10,
    "doctor": 5,
    "appointment": 50,
    "notes": "Patient diagnosed with hypertension. Blood pressure: 140/90.",
    "prescription": "Amlodipine 5mg once daily. Low sodium diet.",
    "follow_up_required": true,
    "created_at": "2025-12-09T15:00:00Z"
  }
]
```

#### 3. Get Single Treatment
**GET** `/treatments/{id}/`

**Permission**: Authenticated

**Response:** (200 OK) - Same as list item

#### 4. Update Treatment
**PUT/PATCH** `/treatments/{id}/`

**Permission**: Doctor only (own treatments)

**Request:**
```json
{
  "notes": "Patient showed improvement. Blood pressure: 130/85.",
  "prescription": "Continue Amlodipine 5mg. Follow up in 2 weeks.",
  "follow_up_required": true
}
```

> **Note**: This is how follow-up appointments update the same treatment record.

#### 5. Delete Treatment
**DELETE** `/treatments/{id}/`

**Permission**: Doctor only (own treatments)

**Response:** (204 No Content)

---

### Payments App (`/payments/`)

#### 1. Create Payment
**POST** `/payments/`

**Permission**: Authenticated

**Request (Cash):**
```json
{
  "patient_id": 10,
  "amount": "500.00",
  "payment_method": "cash"
}
```

**Response:** (201 Created)
```json
{
  "id": 15,
  "patient_id": 10,
  "amount": "500.00",
  "payment_method": "cash",
  "status": "paid",
  "reference": "a8b7c6d5-e4f3-g2h1-i0j9-k8l7m6n5o4p3",
  "created_at": "2025-12-09T14:30:00Z",
  "updated_at": "2025-12-09T14:30:00Z"
}
```

**Request (Chapa):**
```json
{
  "patient_id": 10,
  "amount": "500.00",
  "payment_method": "chapa"
}
```

**Response:** (201 Created)
```json
{
  "payment_url": "https://checkout.chapa.co/checkout/payment/...",
  "reference": "b9c8d7e6-f5g4-h3i2-j1k0-l9m8n7o6p5q4"
}
```

#### 2. Payment Webhook (Chapa Callback)
**POST** `/payments/webhook/`

**Permission**: AllowAny (public endpoint for Chapa)

**Request:**
```json
{
  "tx_ref": "b9c8d7e6-f5g4-h3i2-j1k0-l9m8n7o6p5q4"
}
```

**Response:** (200 OK)
```json
{
  "message": "Payment status updated",
  "status": "paid"
}
```

> **Note**: This endpoint is called by Chapa after payment completion. It verifies the payment and updates status.

#### 3. List All Payments
**GET** `/payments/`

**Permission**: Authenticated

**Response:** (200 OK)
```json
[
  {
    "id": 15,
    "patient": 10,
    "amount": "500.00",
    "payment_method": "cash",
    "reference": "a8b7c6d5-e4f3-g2h1-i0j9-k8l7m6n5o4p3",
    "status": "paid",
    "created_at": "2025-12-09T14:30:00Z",
    "updated_at": "2025-12-09T14:30:00Z"
  }
]
```

#### 4. Get Single Payment
**GET** `/payments/{id}/`

**Permission**: Authenticated

**Response:** (200 OK) - Same as list item

#### 5. Update Payment
**PUT/PATCH** `/payments/{id}/`

**Permission**: Authenticated

**Request:**
```json
{
  "status": "failed"
}
```

#### 6. Delete Payment
**DELETE** `/payments/{id}/`

**Permission**: Authenticated

**Response:** (204 No Content)

---

### API Documentation Endpoints

#### OpenAPI Schema
**GET** `/schema/`

Returns the complete OpenAPI 3.0 schema (JSON format)

#### Swagger UI
**GET** `/schema/swagger-ui/`

Interactive API documentation with Swagger UI

#### ReDoc
**GET** `/schema/redoc/`

Beautiful API documentation with ReDoc

---

## Data Models

### User Model
```python
{
  "id": Integer,
  "username": String (unique),
  "email": String,
  "first_name": String,
  "last_name": String,
  "role": Choice["admin", "doctor", "receptionist"],
  "password": String (hashed)
}
```

### Patient Model
```python
{
  "id": Integer,
  "first_name": String,
  "last_name": String,
  "date_of_birth": Date (nullable),
  "gender": Choice["M", "F"],
  "contact_number": String,
  "address": Text,
  "assigned_doctor": ForeignKey(User),
  "queue_number": Integer (auto-increment daily),
  "is_seen": Boolean,
  "created_at": DateTime,
  "updated_at": DateTime
}
```

### Appointment Model
```python
{
  "id": Integer,
  "patient": ForeignKey(Patient),
  "doctor": ForeignKey(User),
  "appointment_date": DateTime,
  "appointment_type": Choice["initial", "follow_up"],
  "initial_appointment": ForeignKey(Appointment, nullable),
  "treatment": ForeignKey(Treatment, nullable),
  "type_seq": Integer (auto per type),
  "case_followup_seq": Integer (auto per initial),
  "notes": Text,
  "status": Choice["pending", "completed", "cancelled"],
  "created_at": DateTime,
  "updated_at": DateTime
}
```

**Constraints:**
- Initial appointments: `treatment` must be NULL
- Follow-up appointments: `treatment` must NOT be NULL
- Follow-up appointments: `initial_appointment` must reference an initial appointment

### Treatment Model
```python
{
  "id": Integer,
  "patient": ForeignKey(Patient) [unique],
  "doctor": ForeignKey(User),
  "appointment": ForeignKey(Appointment),
  "notes": Text,
  "prescription": Text (nullable),
  "follow_up_required": Boolean,
  "created_at": DateTime
}
```

**Constraints:**
- One treatment per patient (unique constraint)

### Payment Model
```python
{
  "id": Integer,
  "patient": ForeignKey(Patient),
  "amount": Decimal,
  "payment_method": Choice["cash", "chapa"],
  "reference": String (unique UUID),
  "status": Choice["pending", "paid", "failed"],
  "created_at": DateTime,
  "updated_at": DateTime
}
```

**Constraints:**
- One successful payment per patient

---

## Authentication & Security

### JWT Authentication
- **Access Token**: Valid for 1 day
- **Refresh Token**: Valid for 7 days
- Tokens issued on login

### Role-Based Permissions

| Endpoint                  | Admin | Doctor | Receptionist |
|---------------------------|-------|--------|--------------|
| Register users            | ✅    | ❌     | ❌           |
| Login                     | ✅    | ✅     | ✅           |
| View all users            | ✅    | ❌     | ❌           |
| Register patient          | ❌    | ❌     | ✅           |
| View all patients         | ✅    | ❌     | ✅           |
| View single patient       | ✅    | ✅     | ✅           |
| Update patient            | ❌    | ❌     | ✅           |
| Delete patient            | ✅    | ❌     | ❌           |
| View appointments         | ✅    | ✅     | ✅           |
| Create follow-up          | ❌    | ✅     | ❌           |
| Update appointment        | ❌    | ✅     | ❌           |
| Delete appointment        | ✅    | ❌     | ❌           |
| Create/update treatment   | ❌    | ✅     | ❌           |
| View treatments           | ✅    | ✅ *   | ❌           |
| Create payment            | ✅    | ✅     | ✅           |
| View payments             | ✅    | ✅     | ✅           |

*Doctors can only view their own treatments

### Caching Strategy
- Redis-based caching with configurable TTL
- Cache invalidation on create/update/delete operations
- Cached endpoints:
  - User list and profile
  - Patient list and details
  - Appointment lists (grouped and today's)

### Environment Variables
```env
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=hospital_db
DB_USER=postgres
DB_PASSWORD=your_password

# Security
DJANGO_SECRET_KEY=your-secret-key
DJANGO_DEBUG=false
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# Payment
DEFAULT_PAYMENT_EMAIL=payments@hospital.com
PAYMENT_RETURN_URL=http://localhost:3000/payment-success
CHAPA_SECRET_KEY=your-chapa-secret-key

# Cache
CACHE_URL=redis://127.0.0.1:6379/1
CACHE_TTL=86400
CACHE_KEY_PREFIX=hospital_mgmt
```

---

## Summary

This Hospital Management System provides a complete solution for managing patient care from registration through treatment and follow-ups. The three-tier role system ensures proper access control, while the integrated payment processing and automatic workflow management streamline hospital operations.

**Key Points:**
- Admins create users manually
- Receptionists register patients and collect fees
- Initial appointments auto-created on registration
- Doctors provide treatment and schedule follow-ups
- One treatment record per patient (persists across follow-ups)
- Follow-up appointments linked to initial appointments and treatments
- Comprehensive API with JWT authentication and role-based access
- Performance optimized with Redis caching
