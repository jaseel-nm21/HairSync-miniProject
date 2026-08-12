"""
Authentication Routes
Handles User Registration, Login, Logout, Session management, and Role protection.
"""

import re
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models.user import User
from models.donor import Donor
from models.ngo import NGO
from models.recipient import Recipient

auth_bp = Blueprint('auth', __name__)

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')


def get_role_dashboard(role):
    """Returns endpoint URL for given user role."""
    mapping = {
        'admin': 'admin.dashboard',
        'ngo': 'ngo.dashboard',
        'donor': 'donor.dashboard',
        'recipient': 'recipient.dashboard'
    }
    return mapping.get(role, 'index')


def login_required(f):
    """Decorator to ensure route is only accessed by logged-in users."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            session['next_url'] = request.url
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def role_required(*allowed_roles):
    """Decorator to restrict route access by role."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in to access this page.', 'warning')
                session['next_url'] = request.url
                return redirect(url_for('auth.login'))

            user_role = session.get('role')
            if user_role not in allowed_roles:
                flash('Access denied. You do not have permission to view this resource.', 'danger')
                return redirect(url_for(get_role_dashboard(user_role)))

            return f(*args, **kwargs)
        return decorated_function
    return decorator


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login with email and password authentication."""
    if 'user_id' in session:
        return redirect(url_for(get_role_dashboard(session.get('role'))))

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        remember = request.form.get('remember')

        if not email or not password:
            flash('Please provide both email and password.', 'danger')
            return render_template('login.html', email=email)

        user = User.get_by_email(email)
        if not user or not User.verify_password(user['password_hash'], password):
            flash('Invalid email address or password. Please try again.', 'danger')
            return render_template('login.html', email=email)

        if user['status'] == 'suspended':
            flash('Your account has been suspended. Please contact administrator.', 'danger')
            return render_template('login.html', email=email)

        # Establish session
        session.clear()
        session['user_id'] = user['id']
        session['user_name'] = user['name']
        session['user_email'] = user['email']
        session['role'] = user['role']
        session.permanent = bool(remember)

        # Cache NGO approval status in session if role is NGO
        if user['role'] == 'ngo':
            ngo_profile = NGO.get_by_user_id(user['id'])
            session['approval_status'] = ngo_profile['approval_status'] if ngo_profile else 'pending'

        flash(f'Welcome back, {user["name"]}!', 'success')

        next_url = session.pop('next_url', None)
        if next_url and next_url.startswith('/'):
            return redirect(next_url)

        return redirect(url_for(get_role_dashboard(user['role'])))

    return render_template('login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Unified user registration for Donors, NGOs, and Recipients."""
    if 'user_id' in session:
        return redirect(url_for(get_role_dashboard(session.get('role'))))

    # Pre-select role if passed via query param (e.g., /register?role=donor)
    selected_role = request.args.get('role', 'donor').lower()
    if selected_role not in ['donor', 'ngo', 'recipient']:
        selected_role = 'donor'

    if request.method == 'POST':
        role = request.form.get('role', 'donor').lower()
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        district = request.form.get('district', '').strip()

        # General validations
        errors = []
        if not name:
            errors.append('Name is required.')
        if not email or not EMAIL_REGEX.match(email):
            errors.append('A valid email address is required.')
        if not password or len(password) < 6:
            errors.append('Password must be at least 6 characters long.')
        if password != confirm_password:
            errors.append('Passwords do not match.')
        if not phone:
            errors.append('Phone number is required.')
        if not address:
            errors.append('Address is required.')
        if not district:
            errors.append('District is required.')

        # Check existing user email
        if User.get_by_email(email):
            errors.append('An account with this email address already exists.')

        # Role-specific fields
        org_name = request.form.get('org_name', '').strip()
        reg_number = request.form.get('reg_number', '').strip()
        description = request.form.get('description', '').strip()

        dob = request.form.get('dob', '').strip()
        reason = request.form.get('reason', '').strip()

        hair_length = request.form.get('hair_length', '').strip()
        hair_type = request.form.get('hair_type', '').strip()
        hair_condition = request.form.get('hair_condition', '').strip()

        if role == 'ngo':
            if not org_name:
                errors.append('Organization Name is required.')
            if not reg_number:
                errors.append('Official Registration Number is required.')
            elif NGO.get_by_reg_no(reg_number):
                errors.append('An NGO with this Registration Number already exists.')
        elif role == 'recipient':
            if not dob:
                errors.append('Date of birth is required.')
            if not reason:
                errors.append('Reason for requesting a wig is required.')

        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template(
                'register.html',
                role=role,
                name=name,
                email=email,
                phone=phone,
                address=address,
                district=district,
                org_name=org_name,
                reg_number=reg_number,
                description=description,
                dob=dob,
                reason=reason,
                hair_length=hair_length,
                hair_type=hair_type,
                hair_condition=hair_condition
            )

        # Create user account
        user_status = 'pending' if role == 'ngo' else 'active'
        user_id = User.create(
            name=org_name if role == 'ngo' else name,
            email=email,
            password=password,
            role=role,
            status=user_status
        )

        # Automatically establish authenticated session
        session.clear()
        session['user_id'] = user_id
        session['user_name'] = org_name if role == 'ngo' else name
        session['user_email'] = email
        session['role'] = role
        if role == 'ngo':
            session['approval_status'] = 'pending'

        # Create corresponding profile
        if role == 'donor':
            Donor.create(
                user_id=user_id,
                phone=phone,
                address=address,
                district=district,
                hair_length=hair_length if hair_length else None,
                hair_type=hair_type if hair_type else None,
                hair_condition=hair_condition if hair_condition else None
            )
            flash('Registration successful! Welcome to the HairSync Donor Community.', 'success')

        elif role == 'ngo':
            NGO.create(
                user_id=user_id,
                organization_name=org_name,
                registration_number=reg_number,
                phone=phone,
                email=email,
                address=address,
                district=district,
                description=description,
                approval_status='pending'
            )
            flash('NGO Registration submitted successfully! Your account is currently pending administrative approval.', 'warning')

        elif role == 'recipient':
            Recipient.create(
                user_id=user_id,
                phone=phone,
                address=address,
                district=district,
                date_of_birth=dob,
                reason_for_wig=reason
            )
            flash('Registration successful! Your recipient profile has been created.', 'success')

        return redirect(url_for(get_role_dashboard(role)))

    return render_template('register.html', role=selected_role)


@auth_bp.route('/logout', methods=['GET', 'POST'])
def logout():
    """Logs the user out by clearing session variables."""
    user_name = session.get('user_name', 'User')
    session.clear()
    flash(f'Goodbye {user_name}! You have been logged out securely.', 'info')
    return redirect(url_for('auth.login'))
