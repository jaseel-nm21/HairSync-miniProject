"""
Donor Routes (Module 1, 2 & 3)
Handles Donor dashboard, hair profile view, photo upload, eligibility questionnaire,
appointment scheduling & lifecycle, and personal hair donation history.
"""

import os
import time
from datetime import datetime, date
from werkzeug.utils import secure_filename
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from routes.auth import role_required
from models.user import User
from models.donor import Donor
from models.ngo import NGO
from models.donation_center import DonationCenter
from models.donation_guideline import DonationGuideline
from models.appointment import Appointment
from models.donation import Donation
from config import Config

donor_bp = Blueprint('donor', __name__, url_prefix='/donor')


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS


@donor_bp.route('/dashboard')
@role_required('donor')
def dashboard():
    """Donor dashboard overview with profile summary, upcoming appointments, and donation impact."""
    user_id = session.get('user_id')
    user = User.get_by_id(user_id)
    profile = Donor.get_by_user_id(user_id)

    # Calculate profile completion percentage
    fields = [
        profile.get('phone') if profile else None,
        profile.get('address') if profile else None,
        profile.get('district') if profile else None,
        profile.get('hair_length') if profile else None,
        profile.get('hair_type') if profile else None,
        profile.get('hair_condition') if profile else None,
        profile.get('photo') if profile else None
    ]
    completed_fields = sum(1 for f in fields if f)
    completion_percentage = int((completed_fields / len(fields)) * 100)

    # Module 3 metrics
    recent_appointments = []
    donation_stats = {'count': 0, 'total_length': 0.0}
    if profile:
        recent_appointments = Appointment.get_by_donor(profile['id'])[:3]
        donation_stats = Donation.count_by_donor(profile['id'])

    return render_template(
        'donor/dashboard.html',
        user=user,
        profile=profile,
        completion_percentage=completion_percentage,
        recent_appointments=recent_appointments,
        donation_stats=donation_stats
    )


@donor_bp.route('/profile', methods=['GET', 'POST'])
@role_required('donor')
def profile():
    """View and update donor profile information including hair specs and photo."""
    user_id = session.get('user_id')
    user = User.get_by_id(user_id)
    profile_data = Donor.get_by_user_id(user_id)

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        district = request.form.get('district', '').strip()
        hair_length = request.form.get('hair_length', '').strip()
        hair_type = request.form.get('hair_type', '').strip()
        hair_condition = request.form.get('hair_condition', '').strip()

        # Validation
        if not name or not phone or not address or not district:
            flash('Name, phone, address, and district are mandatory fields.', 'danger')
            return render_template('donor/profile.html', user=user, profile=profile_data)

        # Handle file upload
        photo_filename = profile_data.get('photo') if profile_data else None
        if 'photo' in request.files:
            file = request.files['photo']
            if file and file.filename != '':
                if allowed_file(file.filename):
                    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
                    ext = file.filename.rsplit('.', 1)[1].lower()
                    safe_name = f"donor_{user_id}_{int(time.time())}.{ext}"
                    filepath = os.path.join(Config.UPLOAD_FOLDER, safe_name)
                    file.save(filepath)
                    photo_filename = safe_name
                else:
                    flash('Invalid image format. Allowed formats: PNG, JPG, JPEG, WEBP.', 'danger')
                    return render_template('donor/profile.html', user=user, profile=profile_data)

        # Update User name if changed
        if name != user['name']:
            User.update_name_email(user_id, name, user['email'])
            session['user_name'] = name

        # Update or create donor profile
        Donor.create_or_update(
            user_id=user_id,
            phone=phone,
            address=address,
            district=district,
            hair_length=hair_length if hair_length else None,
            hair_type=hair_type if hair_type else None,
            hair_condition=hair_condition if hair_condition else None,
            photo=photo_filename
        )

        flash('Your donor profile has been updated successfully!', 'success')
        return redirect(url_for('donor.dashboard'))

    return render_template('donor/profile.html', user=user, profile=profile_data)


@donor_bp.route('/donation-centers')
@role_required('donor')
def donation_centers():
    """Browse verified active donation collection centers."""
    district_filter = request.args.get('district', 'all').strip()
    search_query = request.args.get('q', '').strip()

    centers = DonationCenter.get_active_or_approved(
        district=district_filter if district_filter.lower() != 'all' else None,
        search=search_query if search_query else None
    )
    districts = DonationCenter.get_distinct_districts()

    return render_template(
        'donor/donation_centers.html',
        centers=centers,
        districts=districts,
        district_filter=district_filter,
        search_query=search_query
    )


@donor_bp.route('/donation-centers/<int:center_id>')
@role_required('donor')
def view_center(center_id):
    """View full details of an approved donation center."""
    center = DonationCenter.get_by_id(center_id)
    if not center or center['status'] not in ['Active', 'Approved']:
        flash('Donation center not found or currently inactive.', 'warning')
        return redirect(url_for('donor.donation_centers'))

    return render_template('ngo/donation_centers/view.html', center=center, is_donor=True)


# ==========================================================
# MODULE 3: ELIGIBILITY QUESTIONNAIRE
# ==========================================================

@donor_bp.route('/eligibility', methods=['GET', 'POST'])
@role_required('donor')
def eligibility():
    """Interactive hair donation eligibility questionnaire and guideline evaluation."""
    user_id = session.get('user_id')
    donor_profile = Donor.get_by_user_id(user_id)
    approved_ngos = NGO.get_all(approval_status='approved')

    evaluation_result = None
    form_data = {
        'ngo_id': request.args.get('ngo_id', ''),
        'hair_length': (donor_profile.get('hair_length') if donor_profile and donor_profile.get('hair_length') else '') or '',
        'hair_type': (donor_profile.get('hair_type') if donor_profile and donor_profile.get('hair_type') else 'Straight') or 'Straight',
        'hair_condition': (donor_profile.get('hair_condition') if donor_profile and donor_profile.get('hair_condition') else 'Virgin/Untreated') or 'Virgin/Untreated',
        'is_colored': False,
        'is_chemically_treated': False,
        'is_bleached': False,
    }

    if request.method == 'POST':
        ngo_id_val = request.form.get('ngo_id', '').strip()
        length_val = request.form.get('hair_length', '').strip()
        type_val = request.form.get('hair_type', '').strip()
        cond_val = request.form.get('hair_condition', '').strip()
        is_colored = request.form.get('is_colored') == 'on'
        is_chem = request.form.get('is_chemically_treated') == 'on'
        is_bleached = request.form.get('is_bleached') == 'on'

        form_data.update({
            'ngo_id': ngo_id_val,
            'hair_length': length_val,
            'hair_type': type_val,
            'hair_condition': cond_val,
            'is_colored': is_colored,
            'is_chemically_treated': is_chem,
            'is_bleached': is_bleached,
        })

        # Fetch guideline for selected NGO or platform default
        guideline = None
        target_ngo = None
        if ngo_id_val and ngo_id_val.isdigit():
            target_ngo = NGO.get_by_id(int(ngo_id_val))
            if target_ngo:
                guideline = DonationGuideline.get_or_default(target_ngo['id'])

        if not guideline:
            guideline = DonationGuideline.DEFAULT_GUIDELINES

        evaluation_result = DonationGuideline.evaluate_donor(
            guideline=guideline,
            hair_length=length_val,
            hair_type=type_val,
            hair_condition=cond_val,
            is_colored=is_colored,
            is_chemically_treated=is_chem,
            is_bleached=is_bleached
        )
        evaluation_result['ngo'] = target_ngo
        evaluation_result['guideline'] = guideline

    return render_template(
        'donor/eligibility.html',
        ngos=approved_ngos,
        form_data=form_data,
        result=evaluation_result
    )


# ==========================================================
# MODULE 3: APPOINTMENT SCHEDULING & LIFECYCLE
# ==========================================================

@donor_bp.route('/appointments/book', methods=['GET', 'POST'])
@role_required('donor')
def book_appointment():
    """Schedule a donation appointment at an active verified center."""
    user_id = session.get('user_id')
    donor_profile = Donor.get_by_user_id(user_id)

    if not donor_profile or not donor_profile.get('phone') or not donor_profile.get('district'):
        flash('Please complete your donor profile details (phone and district) before booking an appointment.', 'warning')
        return redirect(url_for('donor.profile'))

    # Retrieve all active/approved centers
    centers = DonationCenter.get_active_or_approved()
    preselected_center_id = request.args.get('center_id', '')

    if request.method == 'POST':
        center_id_val = request.form.get('center_id', '').strip()
        appt_date_str = request.form.get('appointment_date', '').strip()
        appt_time_str = request.form.get('appointment_time', '').strip()
        purpose = request.form.get('purpose', 'Hair Donation').strip()
        donor_notes = request.form.get('donor_notes', '').strip()

        errors = []
        if not center_id_val or not center_id_val.isdigit():
            errors.append("Please select a valid donation center.")
        if not appt_date_str:
            errors.append("Appointment date is required.")
        if not appt_time_str:
            errors.append("Appointment time is required.")

        # Date validation: cannot be in past
        if appt_date_str:
            try:
                selected_date = datetime.strptime(appt_date_str, '%Y-%m-%d').date()
                if selected_date < date.today():
                    errors.append("Appointment date cannot be in the past.")
            except ValueError:
                errors.append("Invalid appointment date format (expected YYYY-MM-DD).")

        # Validate center exists and is active
        center = None
        if center_id_val and center_id_val.isdigit():
            center = DonationCenter.get_by_id(int(center_id_val))
            if not center or center['status'] not in ('Active', 'Approved'):
                errors.append("Selected donation center is currently inactive or not found.")

        if errors:
            for err in errors:
                flash(err, 'danger')
            return render_template(
                'donor/book_appointment.html',
                centers=centers,
                preselected_center_id=center_id_val,
                donor=donor_profile
            )

        # Create appointment with status 'Pending'
        appt_id = Appointment.create(
            donor_id=donor_profile['id'],
            ngo_id=center['ngo_id'],
            donation_center_id=center['id'],
            appointment_date=appt_date_str,
            appointment_time=appt_time_str,
            purpose=purpose,
            donor_notes=donor_notes if donor_notes else None
        )

        flash(f"Appointment request booked successfully for {appt_date_str} at {center['center_name']}! Awaiting NGO confirmation.", 'success')
        return redirect(url_for('donor.appointments'))

    return render_template(
        'donor/book_appointment.html',
        centers=centers,
        preselected_center_id=preselected_center_id,
        donor=donor_profile,
        today=date.today().strftime('%Y-%m-%d')
    )


@donor_bp.route('/appointments')
@role_required('donor')
def appointments():
    """View appointment history and upcoming scheduled bookings."""
    user_id = session.get('user_id')
    donor_profile = Donor.get_by_user_id(user_id)

    appts = []
    if donor_profile:
        appts = Appointment.get_by_donor(donor_profile['id'])

    return render_template('donor/appointments.html', appointments=appts)


@donor_bp.route('/appointments/<int:appointment_id>/cancel', methods=['POST'])
@role_required('donor')
def cancel_appointment(appointment_id):
    """Cancel a pending or confirmed appointment."""
    user_id = session.get('user_id')
    donor_profile = Donor.get_by_user_id(user_id)

    if not donor_profile:
        flash('Donor profile not found.', 'danger')
        return redirect(url_for('donor.appointments'))

    reason = request.form.get('cancel_reason', '').strip()
    success, msg = Appointment.cancel_by_donor(appointment_id, donor_profile['id'], reason)
    if success:
        flash(msg, 'success')
    else:
        flash(msg, 'danger')

    return redirect(url_for('donor.appointments'))


# ==========================================================
# MODULE 3: DONATION HISTORY
# ==========================================================

@donor_bp.route('/donations')
@role_required('donor')
def donations():
    """View confirmed hair donation history, statistics, and impact."""
    user_id = session.get('user_id')
    donor_profile = Donor.get_by_user_id(user_id)

    donation_list = []
    stats = {'count': 0, 'total_length': 0.0}
    if donor_profile:
        donation_list = Donation.get_by_donor(donor_profile['id'])
        stats = Donation.count_by_donor(donor_profile['id'])

    return render_template(
        'donor/donations.html',
        donations=donation_list,
        stats=stats,
        donor=donor_profile
    )
