# HairSync: A Web-Based Hair Donor and Recipient Management Platform

[![Python Version](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/Framework-Flask%203.x-green.svg)](https://flask.palletsprojects.com/)
[![Database](https://img.shields.io/badge/Database-SQLite-blue.svg)](https://www.sqlite.org/)
[![Frontend](https://img.shields.io/badge/Frontend-Bootstrap%205.3-purple.svg)](https://getbootstrap.com/)
[![Project Phase](https://img.shields.io/badge/Module-1%20Completed-teal.svg)](#)

---

## 📖 Project Overview

**HairSync** is a centralized, web-based digital platform engineered to connect **Hair Donors**, **NGOs / Donation Centers**, and **Medical Wig Recipients** (such as cancer chemotherapy patients, burn survivors, and individuals living with Alopecia Areata).

Traditionally, hair donation is plagued by manual paper records, unstructured phone calls, scattered spreadsheets, and lack of transparency between donors and patients. HairSync solves this by providing:
1. **Centralized Digital Identity**: Role-based access for Donors, NGOs, Recipients, and Platform Administrators.
2. **Transparent Vetting**: Administrative approval lifecycle for NGOs to protect vulnerable patients.
3. **Structured Profiles**: Tracking precise hair specifications (length, texture, virgin status) and medical eligibility criteria.

---

## 🎯 Current Status: Module 1 (Authentication & User Profile Management)

In accordance with the modular development roadmap, **Module 1** has been implemented.

### Module 1 Features Implemented:
- [x] **User Registration**: Unified registration for Donors, NGOs, and Recipients with dynamic, role-specific input forms.
- [x] **User Login**: Secure credential authentication with remember-me session support and quick-test demo logins.
- [x] **User Logout**: Secure session destruction.
- [x] **Password Hashing**: Industry-standard scrypt/pbkdf2 hashing via `werkzeug.security`. Passwords are never stored in plain-text.
- [x] **Session Management**: Server-side Flask session tracking `user_id`, `role`, and `approval_status`.
- [x] **Role-Based Authentication & Route Protection**: Custom `@login_required` and `@role_required` decorators preventing unauthorized URL access.
- [x] **Dynamic Role Redirection**: Users are automatically routed to their role-specific dashboard upon login:
  - Admin &rarr; `/admin/dashboard`
  - NGO &rarr; `/ngo/dashboard`
  - Donor &rarr; `/donor/dashboard`
  - Recipient &rarr; `/recipient/dashboard`
- [x] **NGO Approval Lifecycle**:
  - Registered NGOs are initialized with `approval_status = 'pending'`.
  - Pending NGOs see an informative verification banner and have restricted access to sensitive functions.
  - Platform Admins can inspect government registration numbers and **Approve** or **Reject** NGOs.
- [x] **Donor Profile Management**: View & edit pledged hair length, hair texture, condition (virgin/treated), contact info, and upload hair photos with instant preview.
- [x] **NGO Profile Management**: View & edit organization charter name, registration number, phone hotline, district, and mission statement.
- [x] **Recipient Profile Management**: View & edit date of birth, confidential medical hair loss reason, and parcel delivery address.
- [x] **Admin Dashboard & Controls**:
  - Global metrics (total donors, partner NGOs, recipients, pending reviews).
  - NGO verification queue with one-click Approve/Reject.
  - User directory with account status toggles (activate/deactivate).
- [x] **Form Validation & Flash Messages**: Comprehensive server-side regex and empty-check validation with Bootstrap dismissible alert banners.

---

## 💻 Technology Stack

| Layer | Technology | Description |
| :--- | :--- | :--- |
| **Backend** | Python 3.9+ / Flask 3.x | Lightweight, modular Python web framework |
| **Database** | SQLite (built-in `sqlite3`) | Local relational database with parameterized queries and dictionary rows |
| **Frontend** | HTML5, CSS3, JavaScript | Modern, clean healthcare design with zero Tailwind dependency |
| **UI Framework**| Bootstrap 5.3 + Icons | Responsive grid, accessible modals, cards, and tables |
| **Security** | Werkzeug Security | Secure password hashing (`generate_password_hash`, `check_password_hash`) |
| **Future Tech** | Chart.js &amp; Leaflet.js | Pre-architected for Modules 2, 3, and tracking extensions |

---

## 📁 Project Architecture

```
HairSync/
├── app.py                      # Application factory, error handlers & blueprint registration
├── config.py                   # Environment configuration loader
├── requirements.txt            # Python dependencies (Flask, Werkzeug, python-dotenv, etc.)
├── README.md                   # Project documentation & execution guide
├── .gitignore                  # Git tracking exclusion rules
├── .env.example                # Sample environment configuration
├── .env                        # Local database & secret credentials
│
├── database/
│   ├── hairsync.sql            # Complete SQLite DDL schema and initial seeds
│   ├── db.py                   # SQLite connection and parameterized execution helpers
│   └── init_db.py              # CLI automated database setup script
│
├── models/
│   ├── __init__.py
│   ├── user.py                 # User authentication, queries, status toggles
│   ├── donor.py                # Donor profile CRUD & hair specifications
│   ├── ngo.py                  # NGO profile CRUD & admin approval lifecycle
│   └── recipient.py            # Recipient profile CRUD & medical reasons
│
├── routes/
│   ├── __init__.py
│   ├── auth.py                 # Registration, login, logout, role decorators
│   ├── admin.py                # Admin dashboard, NGO audit, user directory
│   ├── donor.py                # Donor portal, profile editing, photo upload
│   ├── ngo.py                  # NGO portal (pending vs approved), organization details
│   └── recipient.py            # Recipient portal, medical profile editing
│
├── templates/
│   ├── base.html               # Master layout with responsive navbar & alert container
│   ├── index.html              # Landing page (Hero, Cards for Donors/NGOs/Recipients)
│   ├── login.html              # Login with demo account quick-fill buttons
│   ├── register.html           # Unified registration with dynamic role forms
│   │
│   ├── admin/
│   │   ├── dashboard.html      # Central administration & pending NGO review queue
│   │   ├── ngos.html           # Filterable NGO management table (approve/reject)
│   │   ├── users.html          # Comprehensive user accounts directory
│   │   ├── donors.html         # Donor directory
│   │   └── recipients.html     # Recipient directory
│   │
│   ├── donor/
│   │   ├── dashboard.html      # Donor overview, progress bar, guidelines & roadmap
│   │   └── profile.html        # Hair specs form (length, texture, condition, photo upload)
│   │
│   ├── ngo/
│   │   ├── dashboard.html      # NGO portal with pending verification alert banner
│   │   └── profile.html        # Organization profile form
│   │
│   ├── recipient/
│   │   ├── dashboard.html      # Recipient portal with wig status & tracking preview
│   │   └── profile.html        # Medical condition & address update form
│   │
│   └── errors/
│       ├── 404.html            # Friendly Not Found page
│       ├── 500.html            # Server error handler
│       └── db_error.html       # MySQL connection troubleshooting guide
│
└── static/
    ├── css/
    │   └── style.css           # Healthcare theme, color palette, custom cards
    ├── js/
    │   └── script.js           # Dynamic role selector, client validation, photo preview
    ├── uploads/
    │   └── donors/             # Uploaded donor photos
    └── images/                 # Static illustrations and branding
```

---

## 🗄️ Database Design (SQLite)

### Tables & Relationships
1. **`users`**:
   - `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
   - `name` (TEXT)
   - `email` (TEXT UNIQUE)
   - `password_hash` (TEXT)
   - `role` (TEXT CHECK: `'admin'`, `'ngo'`, `'donor'`, `'recipient'`)
   - `status` (TEXT CHECK: `'active'`, `'inactive'`, `'pending'`, `'suspended'`)
   - `created_at`, `updated_at` (TIMESTAMP)

2. **`donor_profiles`**:
   - `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
   - `user_id` (INTEGER UNIQUE FK &rarr; `users.id` ON DELETE CASCADE)
   - `phone` (TEXT)
   - `address` (TEXT), `district` (TEXT)
   - `hair_length` (REAL in inches)
   - `hair_type` (TEXT: Straight, Wavy, Curly, Coily)
   - `hair_condition` (TEXT: Virgin/Untreated, Colored, Gray, Chemically Treated)
   - `photo` (TEXT - filename in `static/uploads/donors/`)
   - `created_at`, `updated_at`

3. **`ngo_profiles`**:
   - `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
   - `user_id` (INTEGER UNIQUE FK &rarr; `users.id` ON DELETE CASCADE)
   - `organization_name` (TEXT)
   - `registration_number` (TEXT UNIQUE)
   - `phone` (TEXT), `email` (TEXT)
   - `address` (TEXT), `district` (TEXT)
   - `description` (TEXT)
   - `approval_status` (TEXT CHECK: `'pending'`, `'approved'`, `'rejected'`)
   - `created_at`, `updated_at`

4. **`recipient_profiles`**:
   - `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
   - `user_id` (INTEGER UNIQUE FK &rarr; `users.id` ON DELETE CASCADE)
   - `phone` (TEXT)
   - `address` (TEXT), `district` (TEXT)
   - `date_of_birth` (DATE)
   - `reason_for_wig` (TEXT)
   - `created_at`, `updated_at`

---

## ⚙️ Installation & Setup Guide

### 1. Prerequisites
Ensure you have:
- **Python 3.9 or newer** (with built-in `sqlite3`)
- **Git**
*(No XAMPP, MySQL Server, or phpMyAdmin required!)*

### 2. Clone / Open Project
```bash
cd "c:\MCA\mini project\HairSync"
```

### 3. Create Virtual Environment & Install Dependencies
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate

# Install required packages
pip install -r requirements.txt
```

### 4. Configure Environment Variables (`.env`)
Verify the `.env` file in the project root:
```env
FLASK_APP=app.py
FLASK_ENV=development
FLASK_DEBUG=1
SECRET_KEY=hairsync_super_secret_key_mca_project_2024
```

### 5. Initialize the SQLite Database
The database is located at `instance/hairsync.db`. You can initialize it using:

```bash
python database/init_db.py
# or: flask init-db
```
*Note: The application also automatically creates and initializes `instance/hairsync.db` on first run if it does not already exist!*

---

## 🚀 Running the Application

Once dependencies and database are set up:

```bash
# Run Flask server
python app.py
```

Open your browser and navigate to:
```
http://127.0.0.1:5000
```

---

## 🔑 Pre-seeded Test Accounts for Evaluation

You can sign in immediately using these pre-configured accounts (or click any of the **Quick Demo Logins** chips on the `/login` page):

| Role | Email | Password | Description / State |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin@hairsync.com` | `Admin@123` | Full administrative control, NGO review queue, user directory |
| **Approved NGO** | `contact@hopehair.org` | `Password@123` | Active partner NGO (Hope Hair Foundation) |
| **Pending NGO** | `info@gracecrown.org` | `Password@123` | Unapproved NGO (Grace Crown Care) showcasing the pending verification banner |
| **Donor** | `donor@example.com` | `Password@123` | Hair donor (Ananya Sharma) with 14.5" wavy hair profile |
| **Recipient** | `recipient@example.com` | `Password@123` | Medical recipient (Meera Nair) with chemotherapy wig application |

---

## 🗺️ Future Roadmap

- **Module 2: NGO & Donation Center Management**
  - Create physical salon donation drop-off centers
  - Edit/delete centers, opening hours, capacity, and salon verification
- **Module 3: Eligibility, Donation & Appointment Booking**
  - Interactive hair donation eligibility checker quiz
  - Appointment booking calendar with participating centers
  - Confirmation, cancellation, and receipt records
- **Advanced Extensions (Post-Module 3)**:
  - **Interactive Geolocation Map**: Leaflet.js + OpenStreetMap showing nearby donation centers with distance calculation.
  - **Wig Tracking Suite**: Recipient custom wig request submission, NGO approval & assignment, tracking ID generation, step-by-step courier status (Dispatched &rarr; In Transit &rarr; Delivered).
  - **Analytics**: Chart.js donation trends and community impact graphs.
