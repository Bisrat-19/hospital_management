# Hospital Management System - Documentation Summary

## Overview
This document provides a summary of all the documentation and API specification files created for your Hospital Management System project.

---

## Deliverables

### 1. **PROJECT_DOCUMENTATION.md**

**Purpose**: Comprehensive project documentation that you can share with anyone who needs to understand the system.

**Contents**:
- System overview and technology stack
- Complete architecture breakdown
- Detailed user roles and permissions (Admin, Receptionist, Doctor)
- Step-by-step workflow from patient registration to follow-up
- In-depth description of all 5 apps (accounts, patients, appointments, treatments, payments)
- Complete API endpoints reference with request/response examples
- Data models and relationships
- Authentication and security details
- Environment variables reference

**Use Case**: Send this document to:
- New team members joining the project
- Frontend developers building the UI
- Stakeholders who need to understand the system
- Documentation for handoff to another developer

---

### 2. **openapi-spec.yaml**

**Purpose**: Handcrafted OpenAPI 3.0 specification for your API.

**Contents**:
- Complete API specification in OpenAPI 3.0 format
- All endpoints with detailed descriptions
- Request/response schemas
- Authentication specifications (JWT Bearer)
- Example requests and responses
- Organized by tags (Authentication, Users, Patients, Appointments, Treatments, Payments)

**Use Case**:
- Import into Swagger UI for interactive documentation
- Import into Postman for API testing
- Use as contract for frontend-backend integration
- Generate API client libraries in various languages

**How to Use**:
1. **Swagger UI**: Copy to your project and access at `/schema/swagger-ui/`
2. **Postman**: Import → Upload Files → Select this YAML file
3. **Online Viewers**: Upload to https://editor.swagger.io/

---

### 3. **hospital_schema_auto_generated.yaml**

**Purpose**: Auto-generated OpenAPI schema directly from your Django project using drf-spectacular.

**Contents**:
- Automatically extracted from your actual code
- Guaranteed to match your current implementation
- Includes all serializer fields and validations
- Generated from your models, serializers, and views

**Use Case**:
- Reference for exact schema as implemented
- Compare with handcrafted spec to ensure consistency
- Use when you want 100% accurate current state

**How to Regenerate**:
```bash
cd /home/bisrat/Projects/hospital_management
source venv/bin/activate
python manage.py spectacular --file schema.yaml
```

---

## Quick Reference: All API Endpoints

### Authentication & Users (`/accounts/`)
- `POST /accounts/auth/login/` - User login (get JWT tokens)
- `POST /accounts/auth/register/` - Register new user (Admin only)
- `GET /accounts/users/` - List all users (Admin only)
- `GET /accounts/users/{id}/` - Get user by ID (Admin only)
- `PUT/PATCH /accounts/users/{id}/` - Update user (Admin only)
- `DELETE /accounts/users/{id}/` - Delete user (Admin only)
- `GET /accounts/users/profile/` - Get current user profile
- `PATCH /accounts/users/{id}/change-password/` - Change password

### Patients (`/patients/`)
- `GET /patients/` - List all patients (Admin/Receptionist)
- `POST /patients/` - Register new patient (Receptionist only)
- `GET /patients/{id}/` - Get patient details (Admin/Receptionist/Doctor)
- `PUT/PATCH /patients/{id}/` - Update patient (Receptionist only)
- `DELETE /patients/{id}/` - Delete patient (Admin only)

### Appointments (`/appointments/`)
- `GET /appointments/` - List all appointments (grouped by type)
- `GET /appointments/today/` - Get today's appointments (Doctor only)
- `POST /appointments/` - Create follow-up appointment (Doctor only)
- `GET /appointments/{id}/` - Get appointment details
- `PUT/PATCH /appointments/{id}/` - Update appointment (Doctor only)
- `DELETE /appointments/{id}/` - Delete appointment (Admin only)

### Treatments (`/treatments/`)
- `GET /treatments/` - List all treatments (Doctors see own only)
- `POST /treatments/` - Create treatment (Doctor only)
- `GET /treatments/{id}/` - Get treatment details
- `PUT/PATCH /treatments/{id}/` - Update treatment (Doctor only)
- `DELETE /treatments/{id}/` - Delete treatment (Doctor only)

### Payments (`/payments/`)
- `GET /payments/` - List all payments
- `POST /payments/` - Create payment (Cash or Chapa)
- `GET /payments/{id}/` - Get payment details
- `PUT/PATCH /payments/{id}/` - Update payment
- `DELETE /payments/{id}/` - Delete payment
- `POST /payments/webhook/` - Chapa payment webhook (public)

---

## System Workflow Summary

### Patient Journey
1. **Patient arrives** → Receptionist registers patient
2. **Payment collected** → Cash (instant) or Chapa (online)
3. **Initial appointment auto-created** → Patient assigned to doctor
4. **Doctor sees patient** → Creates treatment record
5. **Follow-up scheduled** (if needed) → Linked to same treatment
6. **Follow-up visit** → Updates same treatment record
7. **Completion** → Appointment marked as completed

### Key Relationships
- **One patient** → One treatment (persists across follow-ups)
- **Initial appointment** → Created automatically on registration
- **Follow-up appointments** → Link to initial appointment + treatment
- **Payment** → One successful payment per patient
- **Queue number** → Auto-incremented daily

---


## Technology Stack

- **Backend**: Django 5.2.7 + Django REST Framework
- **Database**: PostgreSQL
- **Authentication**: JWT (SimpleJWT)
- **Caching**: Redis
- **Payment**: Chapa (Ethiopian payment gateway)
- **API Docs**: drf-spectacular (OpenAPI 3.0)

---

## Environment Setup

Required environment variables (`.env` file):
```env
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=hospital_db
DB_USER=postgres
DB_PASSWORD=your_password

# Django
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
```

---

## Access Interactive API Documentation

Your project already has built-in API documentation. When your server is running:

1. **Swagger UI**: http://localhost:8000/schema/swagger-ui/
2. **ReDoc**: http://localhost:8000/schema/redoc/
3. **OpenAPI Schema**: http://localhost:8000/schema/

These provide interactive API documentation where you can:
- View all endpoints
- See request/response schemas
- Test API calls directly from the browser
- Download the OpenAPI spec

---

