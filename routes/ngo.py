"""
NGO Routes (Module 1 & Module 2)
Handles NGO dashboard with pending verification alerts, organization profile management,
and physical hair donation center management (CRUD, ownership validation, status checks).
"""

from functools import wraps
from datetime import date, datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from routes.auth import role_required
from models.user import User
from models.ngo import NGO
from models.donation_center import DonationCenter
from models.donation_guideline import DonationGuideline
from models.appointment import Appointment
from models.donation import Donation
from models.inventory import HairInventory, Wig
from models.wig_request import WigRequest

ngo_bp = Blueprint('ngo', __name__, url_prefix='/ngo')


def ngo_approved_required(f):
    """Ensure NGO is logged in and officially approved before managing donation centers."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))

        if session.get('role') != 'ngo':
            flash('Access denied. NGO credentials required.', 'danger')
            return redirect(url_for('index'))

        user_id = session.get('user_id')
        profile = NGO.get_by_user_id(user_id)
        if not profile or profile.get('approval_status') != 'approved':
            flash('Access restricted: Your organization account is pending administrative approval. You cannot manage donation centers until verified.', 'warning')
            return redirect(url_for('ngo.dashboard'))

        return f(*args, **kwargs)
    return decorated_function


def _validate_center_payload(form_data):
    """Validates form input for donation center creation and editing."""
    errors = []
    center_name = form_data.get('center_name', '').strip()
    address = form_data.get('address', '').strip()
    district = form_data.get('district', '').strip()
    city = form_data.get('city', '').strip()
    state = form_data.get('state', 'Kerala').strip()
    pincode = form_data.get('pincode', '').strip()
    phone = form_data.get('phone', '').strip()
    email = form_data.get('email', '').strip()
    opening_time = form_data.get('opening_time', '').strip()
    closing_time = form_data.get('closing_time', '').strip()
    working_days = form_data.get('working_days', '').strip()
    description = form_data.get('description', '').strip()
    lat_str = form_data.get('latitude', '').strip()
    lng_str = form_data.get('longitude', '').strip()
    status = form_data.get('status', 'Active').strip()

    if not center_name:
        errors.append("Center Name is required.")
    if not address:
        errors.append("Address is required.")
    if not district:
        errors.append("District is required.")
    if not city:
        errors.append("City is required.")
    if not pincode:
        errors.append("Pincode is required.")
    elif not pincode.isdigit() or len(pincode) != 6:
        errors.append("Pincode must be a 6-digit numeric code.")
    if not phone:
        errors.append("Phone number is required.")
    if not opening_time:
        errors.append("Opening Time is required.")
    if not closing_time:
        errors.append("Closing Time is required.")
    if not working_days:
        errors.append("Working Days is required.")

    lat_val = None
    if lat_str:
        try:
            lat_val = float(lat_str)
            if not (-90.0 <= lat_val <= 90.0):
                errors.append("Latitude must be between -90.0 and 90.0 degrees.")
        except ValueError:
            errors.append("Latitude must be a valid numeric decimal.")

    lng_val = None
    if lng_str:
        try:
            lng_val = float(lng_str)
            if not (-180.0 <= lng_val <= 180.0):
                errors.append("Longitude must be between -180.0 and 180.0 degrees.")
        except ValueError:
            errors.append("Longitude must be a valid numeric decimal.")

    if status not in ['Active', 'Inactive', 'Pending', 'Approved', 'Rejected']:
        status = 'Active'

    cleaned = {
        'center_name': center_name,
        'address': address,
        'district': district,
        'city': city,
        'state': state or 'Kerala',
        'pincode': pincode,
        'phone': phone,
        'email': email,
        'opening_time': opening_time,
        'closing_time': closing_time,
        'working_days': working_days,
        'description': description,
        'latitude': lat_val,
        'longitude': lng_val,
        'status': status
    }
    return errors, cleaned


@ngo_bp.route('/dashboard')
@role_required('ngo')
def dashboard():
    """NGO dashboard displaying verification status, center statistics, and quick action links."""
    user_id = session.get('user_id')
    user = User.get_by_id(user_id)
    profile = NGO.get_by_user_id(user_id)

    # Sync session approval status
    if profile:
        session['approval_status'] = profile['approval_status']

    is_approved = profile and profile.get('approval_status') == 'approved'

    # Get donation center statistics for this NGO
    center_counts = DonationCenter.get_counts(profile['id']) if profile else {
        'total': 0, 'active': 0, 'inactive': 0, 'pending': 0, 'rejected': 0, 'approved': 0
    }
    recent_centers = DonationCenter.get_by_ngo_id(profile['id'])[:4] if (profile and is_approved) else []

    # Module 3 metrics: appointments & donations
    appointment_counts = Appointment.count_by_ngo(profile['id']) if profile else {
        'total': 0, 'pending': 0, 'confirmed': 0, 'completed': 0, 'cancelled': 0
    }
    donation_counts = Donation.count_by_ngo(profile['id']) if profile else {
        'count': 0, 'total_length': 0.0
    }
    recent_appointments = Appointment.get_by_ngo(profile['id'])[:5] if (profile and is_approved) else []

    # Module 4 & 5 metrics: inventory & wig requests
    hair_stats = HairInventory.count_by_ngo(profile['id']) if profile else {
        'total_items': 0, 'in_stock': 0, 'in_processing': 0, 'used_in_wig': 0
    }
    wig_stats = Wig.count_by_ngo(profile['id']) if profile else {
        'total_wigs': 0, 'available': 0, 'assigned': 0, 'in_transit': 0, 'delivered': 0
    }
    wig_request_stats = WigRequest.count_by_ngo(profile['id']) if profile else {
        'total': 0, 'under_review': 0, 'approved': 0, 'assigned': 0, 'preparing': 0, 'dispatched': 0, 'delivered': 0
    }
    recent_wig_requests = WigRequest.get_by_ngo(profile['id'])[:5] if (profile and is_approved) else []

    return render_template(
        'ngo/dashboard.html',
        user=user,
        profile=profile,
        is_approved=is_approved,
        center_counts=center_counts,
        recent_centers=recent_centers,
        appointment_counts=appointment_counts,
        donation_counts=donation_counts,
        recent_appointments=recent_appointments,
        hair_stats=hair_stats,
        wig_stats=wig_stats,
        wig_request_stats=wig_request_stats,
        recent_wig_requests=recent_wig_requests
    )


@ngo_bp.route('/profile', methods=['GET', 'POST'])
@role_required('ngo')
def profile():
    """View and edit NGO organization details."""
    user_id = session.get('user_id')
    user = User.get_by_id(user_id)
    profile_data = NGO.get_by_user_id(user_id)

    if request.method == 'POST':
        org_name = request.form.get('org_name', '').strip()
        reg_number = request.form.get('reg_number', '').strip()
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip()
        address = request.form.get('address', '').strip()
        district = request.form.get('district', '').strip()
        description = request.form.get('description', '').strip()

        # Validation
        if not org_name or not reg_number or not phone or not email or not address or not district:
            flash('Organization name, registration number, phone, email, address, and district are mandatory.', 'danger')
            return render_template('ngo/profile.html', user=user, profile=profile_data)

        # Check registration number uniqueness if changed
        if profile_data and profile_data['registration_number'] != reg_number:
            existing = NGO.get_by_reg_no(reg_number)
            if existing and existing['user_id'] != user_id:
                flash('Another organization is already registered with this official registration number.', 'danger')
                return render_template('ngo/profile.html', user=user, profile=profile_data)

        # Update User name if organization name changed
        if org_name != user['name']:
            User.update_name_email(user_id, org_name, user['email'])
            session['user_name'] = org_name

        # Update profile
        NGO.create_or_update(
            user_id=user_id,
            organization_name=org_name,
            registration_number=reg_number,
            phone=phone,
            email=email,
            address=address,
            district=district,
            description=description
        )

        flash('Organization profile updated successfully!', 'success')
        return redirect(url_for('ngo.dashboard'))

    return render_template('ngo/profile.html', user=user, profile=profile_data)


@ngo_bp.route('/donation-centers')
@role_required('ngo')
@ngo_approved_required
def donation_centers():
    """List and manage donation centers owned by the logged-in NGO."""
    user_id = session.get('user_id')
    profile_data = NGO.get_by_user_id(user_id)
    search_query = request.args.get('q', '').strip()
    status_filter = request.args.get('status', 'all').strip()

    centers = DonationCenter.get_by_ngo_id(
        ngo_id=profile_data['id'],
        search=search_query if search_query else None,
        status=status_filter if status_filter != 'all' else None
    )
    counts = DonationCenter.get_counts(profile_data['id'])

    return render_template(
        'ngo/donation_centers/index.html',
        centers=centers,
        counts=counts,
        search_query=search_query,
        status_filter=status_filter,
        profile=profile_data
    )


@ngo_bp.route('/donation-centers/add', methods=['GET', 'POST'])
@role_required('ngo')
@ngo_approved_required
def add_center():
    """Create a new donation center for the approved NGO."""
    user_id = session.get('user_id')
    profile_data = NGO.get_by_user_id(user_id)

    if request.method == 'POST':
        errors, cleaned = _validate_center_payload(request.form)
        if errors:
            for err in errors:
                flash(err, 'danger')
            return render_template(
                'ngo/donation_centers/form.html',
                action='add',
                center=request.form,
                profile=profile_data
            )

        new_id = DonationCenter.create(
            ngo_id=profile_data['id'],
            center_name=cleaned['center_name'],
            address=cleaned['address'],
            district=cleaned['district'],
            city=cleaned['city'],
            state=cleaned['state'],
            pincode=cleaned['pincode'],
            phone=cleaned['phone'],
            email=cleaned['email'],
            opening_time=cleaned['opening_time'],
            closing_time=cleaned['closing_time'],
            working_days=cleaned['working_days'],
            description=cleaned['description'],
            latitude=cleaned['latitude'],
            longitude=cleaned['longitude'],
            status=cleaned['status']
        )
        flash(f"Donation Center '{cleaned['center_name']}' created successfully!", 'success')
        return redirect(url_for('ngo.donation_centers'))

    # Default preset from NGO profile
    preset = {
        'state': 'Kerala',
        'district': profile_data['district'] if profile_data else '',
        'phone': profile_data['phone'] if profile_data else '',
        'email': profile_data['email'] if profile_data else '',
        'opening_time': '09:00',
        'closing_time': '17:00',
        'working_days': 'Monday - Saturday',
        'status': 'Active'
    }
    return render_template(
        'ngo/donation_centers/form.html',
        action='add',
        center=preset,
        profile=profile_data
    )


@ngo_bp.route('/donation-centers/<int:center_id>')
@role_required('ngo')
def view_center(center_id):
    """View details of a specific donation center owned by this NGO."""
    user_id = session.get('user_id')
    profile_data = NGO.get_by_user_id(user_id)
    center = DonationCenter.get_by_id(center_id)

    if not center or center['ngo_id'] != profile_data['id']:
        flash('Access denied: You can only view your own donation centers.', 'danger')
        return render_template('errors/403.html', message="ACCESS DENIED: You cannot view another NGO's donation center."), 403

    return render_template(
        'ngo/donation_centers/view.html',
        center=center,
        profile=profile_data
    )


@ngo_bp.route('/donation-centers/<int:center_id>/edit', methods=['GET', 'POST'])
@role_required('ngo')
@ngo_approved_required
def edit_center(center_id):
    """Edit donation center details with strict NGO ownership verification."""
    user_id = session.get('user_id')
    profile_data = NGO.get_by_user_id(user_id)
    center = DonationCenter.get_by_id(center_id)

    if not center:
        flash('Donation center not found.', 'danger')
        return redirect(url_for('ngo.donation_centers'))

    # Strict security check: MUST belong to this NGO
    if center['ngo_id'] != profile_data['id']:
        flash("ACCESS DENIED: You do not have permission to modify another NGO's donation center.", 'danger')
        return render_template('errors/403.html', message="ACCESS DENIED: You cannot modify another NGO's donation center."), 403

    if request.method == 'POST':
        errors, cleaned = _validate_center_payload(request.form)
        if errors:
            for err in errors:
                flash(err, 'danger')
            return render_template(
                'ngo/donation_centers/form.html',
                action='edit',
                center=request.form,
                center_id=center_id,
                profile=profile_data
            )

        success = DonationCenter.update(
            center_id=center_id,
            center_name=cleaned['center_name'],
            address=cleaned['address'],
            district=cleaned['district'],
            city=cleaned['city'],
            state=cleaned['state'],
            pincode=cleaned['pincode'],
            phone=cleaned['phone'],
            email=cleaned['email'],
            opening_time=cleaned['opening_time'],
            closing_time=cleaned['closing_time'],
            working_days=cleaned['working_days'],
            description=cleaned['description'],
            latitude=cleaned['latitude'],
            longitude=cleaned['longitude'],
            status=cleaned['status'],
            ngo_id=profile_data['id']
        )

        if not success:
            flash("ACCESS DENIED: Ownership validation failed.", 'danger')
            return render_template('errors/403.html', message="ACCESS DENIED: Ownership validation failed."), 403

        flash(f"Donation Center '{cleaned['center_name']}' updated successfully!", 'success')
        return redirect(url_for('ngo.donation_centers'))

    return render_template(
        'ngo/donation_centers/form.html',
        action='edit',
        center=center,
        center_id=center_id,
        profile=profile_data
    )


@ngo_bp.route('/donation-centers/<int:center_id>/delete', methods=['POST'])
@role_required('ngo')
@ngo_approved_required
def delete_center(center_id):
    """Delete a donation center with strict NGO ownership verification."""
    user_id = session.get('user_id')
    profile_data = NGO.get_by_user_id(user_id)
    center = DonationCenter.get_by_id(center_id)

    if not center:
        flash('Donation center not found.', 'danger')
        return redirect(url_for('ngo.donation_centers'))

    # Strict security check: MUST belong to this NGO
    if center['ngo_id'] != profile_data['id']:
        flash("ACCESS DENIED: You cannot delete another NGO's donation center.", 'danger')
        return render_template('errors/403.html', message="ACCESS DENIED: You cannot delete another NGO's donation center."), 403

    success = DonationCenter.delete(center_id, ngo_id=profile_data['id'])
    if not success:
        flash("ACCESS DENIED: Deletion unauthorized.", 'danger')
        return render_template('errors/403.html', message="ACCESS DENIED: Deletion unauthorized."), 403

    flash(f"Donation center '{center['center_name']}' has been deleted successfully.", 'info')
    return redirect(url_for('ngo.donation_centers'))


# ==========================================================
# MODULE 3: DONATION GUIDELINES
# ==========================================================

@ngo_bp.route('/guidelines', methods=['GET', 'POST'])
@role_required('ngo')
@ngo_approved_required
def guidelines():
    """Configure organization-specific hair donation acceptance criteria."""
    user_id = session.get('user_id')
    profile_data = NGO.get_by_user_id(user_id)
    guide = DonationGuideline.get_or_default(profile_data['id'])

    if request.method == 'POST':
        min_length_str = request.form.get('minimum_hair_length', '').strip()
        hair_types_list = request.form.getlist('allowed_hair_types')
        hair_types_custom = request.form.get('allowed_hair_types_custom', '').strip()
        allow_colored = request.form.get('allow_colored_hair', 'Requires Review').strip()
        allow_chem = request.form.get('allow_chemically_treated', 'Not Allowed').strip()
        allow_bleached = request.form.get('allow_bleached_hair', 'Not Allowed').strip()
        min_condition = request.form.get('minimum_condition', '').strip()
        additional_req = request.form.get('additional_requirements', '').strip()

        errors = []
        try:
            min_length = float(min_length_str)
            if min_length <= 0:
                errors.append("Minimum hair length must be greater than 0 cm.")
        except (ValueError, TypeError):
            errors.append("Please enter a valid numeric minimum hair length.")

        # Consolidate hair types
        all_types = list(hair_types_list)
        if hair_types_custom:
            for t in hair_types_custom.split(','):
                if t.strip() and t.strip() not in all_types:
                    all_types.append(t.strip())

        if not all_types:
            all_types = ['Straight', 'Wavy', 'Curly', 'Coily']
        allowed_types_str = ', '.join(all_types)

        valid_choices = ('Allowed', 'Requires Review', 'Not Allowed')
        if allow_colored not in valid_choices:
            allow_colored = 'Requires Review'
        if allow_chem not in valid_choices:
            allow_chem = 'Not Allowed'
        if allow_bleached not in valid_choices:
            allow_bleached = 'Not Allowed'

        if errors:
            for err in errors:
                flash(err, 'danger')
            return render_template('ngo/guidelines.html', guide=guide, profile=profile_data)

        DonationGuideline.upsert(
            ngo_id=profile_data['id'],
            minimum_hair_length=min_length,
            allowed_hair_types=allowed_types_str,
            allow_colored_hair=allow_colored,
            allow_chemically_treated=allow_chem,
            allow_bleached_hair=allow_bleached,
            minimum_condition=min_condition if min_condition else None,
            additional_requirements=additional_req if additional_req else None
        )

        flash('Hair donation criteria and guidelines saved successfully!', 'success')
        return redirect(url_for('ngo.guidelines'))

    return render_template('ngo/guidelines.html', guide=guide, profile=profile_data)


# ==========================================================
# MODULE 3: APPOINTMENTS MANAGEMENT
# ==========================================================

@ngo_bp.route('/appointments')
@role_required('ngo')
@ngo_approved_required
def appointments():
    """View and manage appointments booked for this NGO's collection centers."""
    user_id = session.get('user_id')
    profile_data = NGO.get_by_user_id(user_id)
    status_filter = request.args.get('status', 'all').strip()

    if status_filter not in ['Pending', 'Confirmed', 'Completed', 'Cancelled', 'Rejected']:
        status_filter = 'all'

    appts = Appointment.get_by_ngo(
        profile_data['id'],
        status=status_filter if status_filter != 'all' else None
    )
    counts = Appointment.count_by_ngo(profile_data['id'])

    return render_template(
        'ngo/appointments.html',
        appointments=appts,
        status_filter=status_filter,
        counts=counts,
        profile=profile_data
    )


@ngo_bp.route('/appointments/<int:appointment_id>/confirm', methods=['POST'])
@role_required('ngo')
@ngo_approved_required
def confirm_appointment(appointment_id):
    """Confirm a pending appointment."""
    user_id = session.get('user_id')
    profile_data = NGO.get_by_user_id(user_id)
    appt = Appointment.get_by_id(appointment_id)

    if not appt:
        flash('Appointment record not found.', 'danger')
        return redirect(url_for('ngo.appointments'))

    if appt['ngo_id'] != profile_data['id']:
        flash("ACCESS DENIED: You cannot manage appointments for another NGO.", 'danger')
        return render_template('errors/403.html', message="ACCESS DENIED: Unauthorized appointment access."), 403

    notes = request.form.get('ngo_notes', '').strip()
    Appointment.update_status(appointment_id, 'Confirmed', ngo_notes=notes if notes else appt.get('ngo_notes'))
    flash(f"Appointment #{appointment_id} for {appt['donor_name']} has been Confirmed.", 'success')
    return redirect(url_for('ngo.appointments'))


@ngo_bp.route('/appointments/<int:appointment_id>/reject', methods=['POST'])
@role_required('ngo')
@ngo_approved_required
def reject_appointment(appointment_id):
    """Reject a pending appointment with reason/notes."""
    user_id = session.get('user_id')
    profile_data = NGO.get_by_user_id(user_id)
    appt = Appointment.get_by_id(appointment_id)

    if not appt:
        flash('Appointment record not found.', 'danger')
        return redirect(url_for('ngo.appointments'))

    if appt['ngo_id'] != profile_data['id']:
        flash("ACCESS DENIED: You cannot manage appointments for another NGO.", 'danger')
        return render_template('errors/403.html', message="ACCESS DENIED: Unauthorized appointment access."), 403

    reason = request.form.get('ngo_notes', 'Rejected by NGO based on criteria or center capacity.').strip()
    Appointment.update_status(appointment_id, 'Rejected', ngo_notes=reason)
    flash(f"Appointment #{appointment_id} has been Rejected.", 'warning')
    return redirect(url_for('ngo.appointments'))


@ngo_bp.route('/appointments/<int:appointment_id>/cancel', methods=['POST'])
@role_required('ngo')
@ngo_approved_required
def cancel_appointment(appointment_id):
    """Cancel an appointment."""
    user_id = session.get('user_id')
    profile_data = NGO.get_by_user_id(user_id)
    appt = Appointment.get_by_id(appointment_id)

    if not appt:
        flash('Appointment record not found.', 'danger')
        return redirect(url_for('ngo.appointments'))

    if appt['ngo_id'] != profile_data['id']:
        flash("ACCESS DENIED: You cannot manage appointments for another NGO.", 'danger')
        return render_template('errors/403.html', message="ACCESS DENIED: Unauthorized appointment access."), 403

    reason = request.form.get('ngo_notes', 'Cancelled by center.').strip()
    Appointment.update_status(appointment_id, 'Cancelled', ngo_notes=reason)
    flash(f"Appointment #{appointment_id} has been marked as Cancelled.", 'info')
    return redirect(url_for('ngo.appointments'))


@ngo_bp.route('/appointments/<int:appointment_id>/complete', methods=['GET', 'POST'])
@role_required('ngo')
@ngo_approved_required
def complete_appointment(appointment_id):
    """Record fulfillment of hair donation and complete the appointment."""
    user_id = session.get('user_id')
    profile_data = NGO.get_by_user_id(user_id)
    appt = Appointment.get_by_id(appointment_id)

    if not appt:
        flash('Appointment record not found.', 'danger')
        return redirect(url_for('ngo.appointments'))

    if appt['ngo_id'] != profile_data['id']:
        flash("ACCESS DENIED: You cannot manage appointments for another NGO.", 'danger')
        return render_template('errors/403.html', message="ACCESS DENIED: Unauthorized appointment access."), 403

    if request.method == 'POST':
        hair_length_str = request.form.get('hair_length', '').strip()
        hair_type = request.form.get('hair_type', '').strip()
        hair_condition = request.form.get('hair_condition', '').strip()
        donation_date_str = request.form.get('donation_date', '').strip()
        weight_or_qty = request.form.get('quantity_or_estimated_weight', '').strip()
        notes = request.form.get('notes', '').strip()

        errors = []
        try:
            length_val = float(hair_length_str)
            if length_val <= 0:
                errors.append("Actual measured hair length must be greater than 0 cm.")
        except (ValueError, TypeError):
            errors.append("Please provide a valid numeric hair length.")

        if not hair_type:
            errors.append("Hair type is required.")
        if not hair_condition:
            errors.append("Hair condition is required.")
        if not donation_date_str:
            donation_date_str = date.today().strftime('%Y-%m-%d')

        if errors:
            for err in errors:
                flash(err, 'danger')
            return render_template('ngo/complete_donation.html', appointment=appt, profile=profile_data)

        # Create permanent donation record
        don_id = Donation.create(
            donor_id=appt['donor_id'],
            ngo_id=profile_data['id'],
            donation_center_id=appt['donation_center_id'],
            hair_length=length_val,
            hair_type=hair_type,
            hair_condition=hair_condition,
            donation_date=donation_date_str,
            appointment_id=appt['id'],
            quantity_or_estimated_weight=weight_or_qty if weight_or_qty else None,
            notes=notes if notes else None,
            status='Completed'
        )

        # Automatically catalog fulfilled donation into NGO hair inventory
        try:
            HairInventory.auto_add_from_donation(don_id)
        except Exception as inv_err:
            pass

        # Mark appointment status as 'Completed'
        Appointment.update_status(
            appointment_id=appointment_id,
            new_status='Completed',
            ngo_notes=(appt.get('ngo_notes') or '') + f"\nDonation completed on {donation_date_str}. Measured length: {length_val} cm."
        )

        flash(f"Hair donation successfully recorded for {appt['donor_name']}! Appointment is now marked as Completed.", 'success')
        return redirect(url_for('ngo.donations'))

    return render_template(
        'ngo/complete_donation.html',
        appointment=appt,
        profile=profile_data,
        today=date.today().strftime('%Y-%m-%d')
    )


# ==========================================================
# MODULE 3: NGO DONATIONS REPOSITORY
# ==========================================================

@ngo_bp.route('/donations')
@role_required('ngo')
@ngo_approved_required
def donations():
    """View all fulfilled hair donations recorded by this NGO."""
    user_id = session.get('user_id')
    profile_data = NGO.get_by_user_id(user_id)

    donation_list = Donation.get_by_ngo(profile_data['id'])
    stats = Donation.count_by_ngo(profile_data['id'])

    return render_template(
        'ngo/donations.html',
        donations=donation_list,
        stats=stats,
        profile=profile_data
    )


# ==========================================================
# MODULE 4: HAIR INVENTORY MANAGEMENT
# ==========================================================

@ngo_bp.route('/inventory/hair')
@role_required('ngo')
@ngo_approved_required
def hair_inventory():
    """View and manage collected raw hair inventory for this NGO."""
    user_id = session.get('user_id')
    profile_data = NGO.get_by_user_id(user_id)

    status_filter = request.args.get('status', 'all').strip()
    hair_type_filter = request.args.get('hair_type', 'all').strip()

    if status_filter not in HairInventory.VALID_STATUSES:
        status_filter = 'all'
    if hair_type_filter == 'all':
        hair_type_filter = None

    items = HairInventory.get_by_ngo(
        ngo_id=profile_data['id'],
        status=status_filter if status_filter != 'all' else None,
        hair_type=hair_type_filter
    )
    stats = HairInventory.count_by_ngo(profile_data['id'])

    return render_template(
        'ngo/inventory_hair.html',
        items=items,
        stats=stats,
        status_filter=status_filter,
        hair_type_filter=hair_type_filter or 'all',
        profile=profile_data
    )


@ngo_bp.route('/inventory/hair/add', methods=['POST'])
@role_required('ngo')
@ngo_approved_required
def add_hair_inventory():
    """Manually record a collected or acquired hair bundle into inventory."""
    user_id = session.get('user_id')
    profile_data = NGO.get_by_user_id(user_id)

    hair_type = request.form.get('hair_type', '').strip()
    hair_length_str = request.form.get('hair_length', '').strip()
    hair_condition = request.form.get('hair_condition', '').strip()
    quantity_or_weight = request.form.get('quantity_or_weight', '').strip()
    status = request.form.get('status', 'In Stock').strip()
    notes = request.form.get('notes', '').strip()

    errors = []
    if not hair_type:
        errors.append("Hair type is required.")
    if not hair_condition:
        errors.append("Hair condition is required.")

    length_val = 0.0
    try:
        length_val = float(hair_length_str)
        if length_val <= 0:
            errors.append("Hair length must be greater than 0 cm.")
    except (ValueError, TypeError):
        errors.append("Please provide a valid numeric hair length.")

    if errors:
        for err in errors:
            flash(err, 'danger')
        return redirect(url_for('ngo.hair_inventory'))

    HairInventory.create(
        ngo_id=profile_data['id'],
        hair_type=hair_type,
        hair_length=length_val,
        hair_condition=hair_condition,
        quantity_or_weight=quantity_or_weight if quantity_or_weight else None,
        status=status,
        notes=notes if notes else None
    )

    flash(f"Hair bundle ({length_val} cm, {hair_type}) added to inventory successfully!", 'success')
    return redirect(url_for('ngo.hair_inventory'))


@ngo_bp.route('/inventory/hair/<int:item_id>/status', methods=['POST'])
@role_required('ngo')
@ngo_approved_required
def update_hair_status(item_id):
    """Update status of a hair inventory item."""
    user_id = session.get('user_id')
    profile_data = NGO.get_by_user_id(user_id)

    item = HairInventory.get_by_id(item_id)
    if not item or item['ngo_id'] != profile_data['id']:
        flash("ACCESS DENIED: Unauthorized inventory access.", 'danger')
        return redirect(url_for('ngo.hair_inventory'))

    new_status = request.form.get('status', '').strip()
    notes = request.form.get('notes', '').strip()
    if new_status in HairInventory.VALID_STATUSES:
        HairInventory.update_status(item_id, new_status, notes if notes else item.get('notes'))
        flash(f"Inventory item #{item_id} status updated to '{new_status}'.", 'success')
    else:
        flash("Invalid status specified.", 'danger')

    return redirect(url_for('ngo.hair_inventory'))


@ngo_bp.route('/inventory/hair/<int:item_id>/delete', methods=['POST'])
@role_required('ngo')
@ngo_approved_required
def delete_hair_inventory(item_id):
    """Delete a hair inventory item."""
    user_id = session.get('user_id')
    profile_data = NGO.get_by_user_id(user_id)

    success = HairInventory.delete(item_id, profile_data['id'])
    if success:
        flash(f"Hair inventory item #{item_id} has been removed.", 'info')
    else:
        flash("Item not found or access denied.", 'danger')

    return redirect(url_for('ngo.hair_inventory'))


# ==========================================================
# MODULE 4: WIG INVENTORY MANAGEMENT
# ==========================================================

@ngo_bp.route('/inventory/wigs')
@role_required('ngo')
@ngo_approved_required
def wig_inventory():
    """View and manage crafted wigs inventory for this NGO."""
    user_id = session.get('user_id')
    profile_data = NGO.get_by_user_id(user_id)

    status_filter = request.args.get('status', 'all').strip()
    source_filter = request.args.get('hair_source', 'all').strip()

    if status_filter not in Wig.VALID_STATUSES:
        status_filter = 'all'
    if source_filter not in Wig.VALID_SOURCES:
        source_filter = 'all'

    wigs = Wig.get_by_ngo(
        ngo_id=profile_data['id'],
        status=status_filter if status_filter != 'all' else None,
        hair_source=source_filter if source_filter != 'all' else None
    )
    stats = Wig.count_by_ngo(profile_data['id'])

    return render_template(
        'ngo/inventory_wigs.html',
        wigs=wigs,
        stats=stats,
        status_filter=status_filter,
        source_filter=source_filter,
        profile=profile_data
    )


@ngo_bp.route('/inventory/wigs/add', methods=['POST'])
@role_required('ngo')
@ngo_approved_required
def add_wig():
    """Add a new crafted natural-hair wig to inventory."""
    user_id = session.get('user_id')
    profile_data = NGO.get_by_user_id(user_id)

    wig_type = request.form.get('wig_type', '').strip()
    hair_source = request.form.get('hair_source', 'Natural').strip()
    hair_color = request.form.get('hair_color', '').strip()
    hair_length_str = request.form.get('hair_length', '').strip()
    size = request.form.get('size', 'Medium').strip()
    condition = request.form.get('condition', 'New / Sanitized').strip()
    status = request.form.get('status', 'Available').strip()
    notes = request.form.get('notes', '').strip()

    errors = []
    if not wig_type:
        errors.append("Wig name / style is required.")
    if not hair_color:
        errors.append("Hair color is required.")

    length_val = 0.0
    try:
        length_val = float(hair_length_str)
        if length_val <= 0:
            errors.append("Wig hair length must be greater than 0 cm.")
    except (ValueError, TypeError):
        errors.append("Please provide a valid numeric hair length.")

    if errors:
        for err in errors:
            flash(err, 'danger')
        return redirect(url_for('ngo.wig_inventory'))

    Wig.create(
        ngo_id=profile_data['id'],
        wig_type=wig_type,
        hair_source=hair_source,
        hair_color=hair_color,
        hair_length=length_val,
        size=size,
        condition=condition,
        status=status,
        notes=notes if notes else None
    )

    flash(f"Wig '{wig_type}' ({hair_source}, {length_val} cm) added to inventory successfully!", 'success')
    return redirect(url_for('ngo.wig_inventory'))


@ngo_bp.route('/inventory/wigs/<int:wig_id>/edit', methods=['POST'])
@role_required('ngo')
@ngo_approved_required
def edit_wig(wig_id):
    """Update details for a specific wig."""
    user_id = session.get('user_id')
    profile_data = NGO.get_by_user_id(user_id)

    wig = Wig.get_by_id(wig_id)
    if not wig or wig['ngo_id'] != profile_data['id']:
        flash("ACCESS DENIED: Unauthorized wig inventory access.", 'danger')
        return redirect(url_for('ngo.wig_inventory'))

    wig_type = request.form.get('wig_type', '').strip()
    hair_source = request.form.get('hair_source', 'Natural').strip()
    hair_color = request.form.get('hair_color', '').strip()
    hair_length_str = request.form.get('hair_length', '').strip()
    size = request.form.get('size', 'Medium').strip()
    condition = request.form.get('condition', 'New / Sanitized').strip()
    status = request.form.get('status', 'Available').strip()
    notes = request.form.get('notes', '').strip()

    try:
        length_val = float(hair_length_str)
    except (ValueError, TypeError):
        length_val = wig['hair_length']

    Wig.update(
        wig_id=wig_id,
        ngo_id=profile_data['id'],
        wig_type=wig_type or wig['wig_type'],
        hair_source=hair_source,
        hair_color=hair_color or wig['hair_color'],
        hair_length=length_val,
        size=size,
        condition=condition,
        status=status,
        notes=notes if notes else None
    )

    flash(f"Wig #{wig_id} '{wig_type}' details updated successfully.", 'success')
    return redirect(url_for('ngo.wig_inventory'))


@ngo_bp.route('/inventory/wigs/<int:wig_id>/delete', methods=['POST'])
@role_required('ngo')
@ngo_approved_required
def delete_wig(wig_id):
    """Delete a wig from inventory."""
    user_id = session.get('user_id')
    profile_data = NGO.get_by_user_id(user_id)

    success, msg = Wig.delete(wig_id, profile_data['id'])
    if success:
        flash(msg, 'success')
    else:
        flash(msg, 'danger')

    return redirect(url_for('ngo.wig_inventory'))


# ==========================================================
# MODULE 5 & 6: RECIPIENT WIG REQUEST MANAGEMENT & FULFILLMENT
# ==========================================================

@ngo_bp.route('/wig-requests')
@role_required('ngo')
@ngo_approved_required
def wig_requests():
    """View incoming and assigned recipient natural-hair wig requests."""
    user_id = session.get('user_id')
    profile_data = NGO.get_by_user_id(user_id)

    status_filter = request.args.get('status', 'all').strip()
    if status_filter not in WigRequest.VALID_STATUSES:
        status_filter = 'all'

    requests_list = WigRequest.get_by_ngo(
        ngo_id=profile_data['id'],
        status=status_filter if status_filter != 'all' else None
    )
    stats = WigRequest.count_by_ngo(profile_data['id'])

    return render_template(
        'ngo/wig_requests.html',
        requests=requests_list,
        stats=stats,
        status_filter=status_filter,
        profile=profile_data
    )


@ngo_bp.route('/wig-requests/<int:request_id>')
@role_required('ngo')
@ngo_approved_required
def view_wig_request(request_id):
    """Detailed review page for a recipient wig request, with wig matching and tracking updates."""
    user_id = session.get('user_id')
    profile_data = NGO.get_by_user_id(user_id)

    req = WigRequest.get_by_id(request_id)
    if not req:
        flash('Wig request record not found.', 'danger')
        return redirect(url_for('ngo.wig_requests'))

    # If assigned to another NGO, prevent access
    if req['ngo_id'] and req['ngo_id'] != profile_data['id']:
        flash("ACCESS DENIED: This wig request is assigned to another organization.", 'danger')
        return render_template('errors/403.html', message="ACCESS DENIED: Unauthorized wig request access."), 403

    timeline = WigRequest.get_tracking_timeline(request_id)
    available_wigs = Wig.get_available_for_ngo(profile_data['id'])

    return render_template(
        'ngo/wig_request_detail.html',
        request_item=req,
        timeline=timeline,
        available_wigs=available_wigs,
        profile=profile_data,
        status_sequence=WigRequest.STATUS_SEQUENCE
    )


@ngo_bp.route('/wig-requests/<int:request_id>/review', methods=['POST'])
@role_required('ngo')
@ngo_approved_required
def review_wig_request(request_id):
    """Mark request as Under Review and claim assignment for this NGO."""
    user_id = session.get('user_id')
    profile_data = NGO.get_by_user_id(user_id)
    remarks = request.form.get('remarks', 'Application is under review by our medical donation team.').strip()

    success, msg = WigRequest.update_status(
        request_id=request_id,
        new_status='Under Review',
        remarks=remarks,
        user_id=user_id,
        ngo_id=profile_data['id']
    )
    flash(msg, 'success' if success else 'danger')
    return redirect(url_for('ngo.view_wig_request', request_id=request_id))


@ngo_bp.route('/wig-requests/<int:request_id>/approve', methods=['POST'])
@role_required('ngo')
@ngo_approved_required
def approve_wig_request(request_id):
    """Approve a recipient wig request."""
    user_id = session.get('user_id')
    profile_data = NGO.get_by_user_id(user_id)
    remarks = request.form.get('remarks', 'Request approved! Natural-hair wig will be prepared/matched.').strip()

    success, msg = WigRequest.update_status(
        request_id=request_id,
        new_status='Approved',
        remarks=remarks,
        user_id=user_id,
        ngo_id=profile_data['id']
    )
    flash(msg, 'success' if success else 'danger')
    return redirect(url_for('ngo.view_wig_request', request_id=request_id))


@ngo_bp.route('/wig-requests/<int:request_id>/reject', methods=['POST'])
@role_required('ngo')
@ngo_approved_required
def reject_wig_request(request_id):
    """Reject a recipient wig request with an explanatory reason."""
    user_id = session.get('user_id')
    profile_data = NGO.get_by_user_id(user_id)
    reason = request.form.get('rejection_reason', 'Criteria not met or outside current allocation quota.').strip()

    success, msg = WigRequest.update_status(
        request_id=request_id,
        new_status='Rejected',
        remarks=f"Request rejected: {reason}",
        rejection_reason=reason,
        user_id=user_id,
        ngo_id=profile_data['id']
    )
    flash(msg, 'warning' if success else 'danger')
    return redirect(url_for('ngo.view_wig_request', request_id=request_id))


@ngo_bp.route('/wig-requests/<int:request_id>/assign', methods=['POST'])
@role_required('ngo')
@ngo_approved_required
def assign_wig_to_request(request_id):
    """Assign an available wig from this NGO's inventory to the approved request."""
    user_id = session.get('user_id')
    profile_data = NGO.get_by_user_id(user_id)
    wig_id_str = request.form.get('wig_id', '').strip()
    remarks = request.form.get('remarks', '').strip()

    if not wig_id_str or not wig_id_str.isdigit():
        flash("Please select a valid available wig from the inventory.", 'danger')
        return redirect(url_for('ngo.view_wig_request', request_id=request_id))

    wig_id = int(wig_id_str)
    success, msg = WigRequest.assign_wig(
        request_id=request_id,
        wig_id=wig_id,
        ngo_id=profile_data['id'],
        remarks=remarks if remarks else None,
        user_id=user_id
    )

    flash(msg, 'success' if success else 'danger')
    return redirect(url_for('ngo.view_wig_request', request_id=request_id))


@ngo_bp.route('/wig-requests/<int:request_id>/update-status', methods=['POST'])
@role_required('ngo')
@ngo_approved_required
def update_wig_request_status(request_id):
    """Advance the fulfillment/dispatch/delivery status of a wig request."""
    user_id = session.get('user_id')
    profile_data = NGO.get_by_user_id(user_id)

    new_status = request.form.get('status', '').strip()
    remarks = request.form.get('remarks', '').strip()
    tracking_number = request.form.get('tracking_number', '').strip()
    courier_service = request.form.get('courier_service', '').strip()
    est_date = request.form.get('estimated_delivery_date', '').strip()

    req = WigRequest.get_by_id(request_id)
    if not req or (req['ngo_id'] and req['ngo_id'] != profile_data['id']):
        flash("ACCESS DENIED: Unauthorized wig request access.", 'danger')
        return redirect(url_for('ngo.wig_requests'))

    success, msg = WigRequest.update_status(
        request_id=request_id,
        new_status=new_status,
        remarks=remarks if remarks else f"Status updated to {new_status}.",
        tracking_number=tracking_number if tracking_number else req.get('tracking_number'),
        courier_service=courier_service if courier_service else req.get('courier_service'),
        estimated_delivery_date=est_date if est_date else req.get('estimated_delivery_date'),
        user_id=user_id,
        ngo_id=profile_data['id']
    )

    flash(msg, 'success' if success else 'danger')
    return redirect(url_for('ngo.view_wig_request', request_id=request_id))



