# Hospital Management System — Backend (Django) 

A simple Django REST API powering hospital operations: users, patients, queues, appointments, treatments, and payments (cash + Chapa). This backend is under active development.

## Status
- Work in progress. Endpoints and database schema may change.

## Tech
- Python 3.11+, Django, Django REST Framework
- PostgreSQL (recommended)
- Redis for caching
- Auth: JWT or session 

## Quick Start
```bash
git clone <repo-url>
cd hospital_management

python -m venv .venv
source .venv/bin/activate  
pip install -r requirements.txt

cp .env.example .env  
python manage.py migrate
python manage.py createsuperuser

python manage.py runserver
```

## Payments (Chapa) — Brief
- Receptionist initiates online payment; system creates tx_ref and checkout link.
- Patient pays via Telebirr/CBE Birr/card.
- Backend verifies via webhook or verify endpoint and marks payment as completed.
- Webhook URL (example): {SITE_URL}/api/payments/chapa/webhook/

## Scope 
- Roles: Admin, Receptionist, Doctor
- Core: patient registration with queueing, doctor assignment, treatments, follow-ups
- Payments: cash and Chapa; receptionist can track pending/paid
- API paths will be under /api/... (subject to change). Docs to be added later.

