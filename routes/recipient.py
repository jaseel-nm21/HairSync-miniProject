"""
Recipient Routes (Module 1, Module 5 & Module 6)
Handles Recipient dashboard, medical profile, natural-hair wig request submission,
request history, and status-based wig tracking timeline.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from routes.auth import role_required
from models.user import User
from models.recipient import Recipient
from models.ngo import NGO
from models.wig_request import WigRequest

recipient_bp = Blueprint('recipient', __name__, url_prefix='/recipient')


@recipient_bp.route('/dashboard')
@role_required('recipient')
def dashboard():
    """Recipient dashboard showing application overview, active wig requests, and tracking."""
    user_id = session.get('user_id')
    user = User.get_by_id(user_id)
    profile = Recipient.get_by_user_id(user_id)

    requests = []
    stats = {'total': 0, 'submitted': 0, 'under_review': 0, 'in_progress': 0, 'dispatched': 0, 'delivered': 0}
    if profile:
        requests = WigRequest.get_by_recipient(profile['id'])
        stats = WigRequest.count_by_recipient(profile['id'])

    # Profile completion check
    fields = [
        profile.get('phone') if profile else None,
        profile.get('address') if profile else None,
        profile.get('district') if profile else None,
        profile.get('date_of_birth') if profile else None,
        profile.get('reason_for_wig') if profile else None
    ]
    completed_fields = sum(1 for f in fields if f)
    completion_percentage = int((completed_fields / len(fields)) * 100) if fields else 0

    return render_template(
        'recipient/dashboard.html',
        user=user,
        profile=profile,
        requests=requests,
        stats=stats,
        completion_percentage=completion_percentage
    )


@recipient_bp.route('/profile', methods=['GET', 'POST'])
@role_required('recipient')
def profile():
    """View and update recipient medical and contact profile."""
    user_id = session.get('user_id')
    user = User.get_by_id(user_id)
    profile_data = Recipient.get_by_user_id(user_id)

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        district = request.form.get('district', '').strip()
        dob = request.form.get('dob', '').strip()
        reason = request.form.get('reason', '').strip()

        # Validation
        if not name or not phone or not address or not district or not dob or not reason:
            flash('All fields are required to keep your recipient application valid.', 'danger')
            return render_template('recipient/profile.html', user=user, profile=profile_data)

        # Update User name if changed
        if name != user['name']:
            User.update_name_email(user_id, name, user['email'])
            session['user_name'] = name

        # Update or create profile
        Recipient.create_or_update(
            user_id=user_id,
            phone=phone,
            address=address,
            district=district,
            date_of_birth=dob,
            reason_for_wig=reason
        )

        flash('Your recipient profile details have been updated successfully!', 'success')
        return redirect(url_for('recipient.dashboard'))

    return render_template('recipient/profile.html', user=user, profile=profile_data)


# ==========================================================
# MODULE 5: NATURAL-HAIR WIG REQUESTS
# ==========================================================

@recipient_bp.route('/requests')
@role_required('recipient')
def requests():
    """View all wig requests submitted by the logged-in recipient."""
    user_id = session.get('user_id')
    profile_data = Recipient.get_by_user_id(user_id)

    if not profile_data:
        flash('Please complete your recipient profile before viewing wig requests.', 'warning')
        return redirect(url_for('recipient.profile'))

    req_list = WigRequest.get_by_recipient(profile_data['id'])
    stats = WigRequest.count_by_recipient(profile_data['id'])

    return render_template(
        'recipient/requests.html',
        requests=req_list,
        stats=stats,
        profile=profile_data
    )


@recipient_bp.route('/requests/new', methods=['GET', 'POST'])
@role_required('recipient')
def new_request():
    """Submit a new natural-hair wig request with preferences and delivery address."""
    user_id = session.get('user_id')
    user = User.get_by_id(user_id)
    profile_data = Recipient.get_by_user_id(user_id)

    if not profile_data or not profile_data.get('phone') or not profile_data.get('address'):
        flash('Please complete your contact and address profile before requesting a wig.', 'warning')
        return redirect(url_for('recipient.profile'))

    approved_ngos = NGO.get_all(approval_status='approved')

    if request.method == 'POST':
        preferred_wig_type = request.form.get('preferred_wig_type', '').strip()
        preferred_length_str = request.form.get('preferred_length', '').strip()
        preferred_color = request.form.get('preferred_color', '').strip()
        preferred_size = request.form.get('preferred_size', 'Medium').strip()
        reason_for_request = request.form.get('reason_for_request', '').strip()
        delivery_address = request.form.get('delivery_address', '').strip()
        delivery_city = request.form.get('delivery_city', '').strip()
        delivery_district = request.form.get('delivery_district', '').strip()
        delivery_pincode = request.form.get('delivery_pincode', '').strip()
        contact_phone = request.form.get('contact_phone', '').strip()
        additional_notes = request.form.get('additional_notes', '').strip()
        ngo_id_str = request.form.get('ngo_id', '').strip()

        errors = []
        if not preferred_wig_type:
            errors.append("Please specify your preferred wig style.")
        if not preferred_color:
            errors.append("Please specify your preferred hair color.")
        if not reason_for_request:
            errors.append("Please share the medical/personal reason for your request.")
        if not delivery_address or not delivery_city or not delivery_district or not delivery_pincode:
            errors.append("Complete delivery address (street, city, district, pincode) is required.")
        elif not delivery_pincode.isdigit() or len(delivery_pincode) != 6:
            errors.append("Pincode must be a 6-digit numeric code.")
        if not contact_phone:
            errors.append("Contact phone number is required for delivery coordination.")

        length_val = 25.0
        try:
            length_val = float(preferred_length_str)
            if length_val <= 0:
                errors.append("Preferred hair length must be greater than 0 cm.")
        except (ValueError, TypeError):
            errors.append("Please provide a valid numeric hair length.")

        ngo_id = int(ngo_id_str) if (ngo_id_str and ngo_id_str.isdigit()) else None

        if errors:
            for err in errors:
                flash(err, 'danger')
            return render_template(
                'recipient/new_request.html',
                user=user,
                profile=profile_data,
                ngos=approved_ngos,
                form_data=request.form
            )

        # Create the wig request
        req_id = WigRequest.create(
            recipient_id=profile_data['id'],
            preferred_wig_type=preferred_wig_type,
            preferred_length=length_val,
            preferred_color=preferred_color,
            preferred_size=preferred_size,
            reason_for_request=reason_for_request,
            delivery_address=delivery_address,
            delivery_city=delivery_city,
            delivery_district=delivery_district,
            delivery_pincode=delivery_pincode,
            contact_phone=contact_phone,
            additional_notes=additional_notes if additional_notes else None,
            ngo_id=ngo_id,
            hair_source='Natural',
            user_id=user_id
        )

        flash('Your natural-hair wig request has been submitted successfully! You can track its progress below.', 'success')
        return redirect(url_for('recipient.track_request', request_id=req_id))

    return render_template(
        'recipient/new_request.html',
        user=user,
        profile=profile_data,
        ngos=approved_ngos
    )


# ==========================================================
# MODULE 6: WIG REQUEST STATUS TRACKING
# ==========================================================

@recipient_bp.route('/requests/<int:request_id>/track')
@role_required('recipient')
def track_request(request_id):
    """View real-time status tracking timeline for a specific wig request."""
    user_id = session.get('user_id')
    profile_data = Recipient.get_by_user_id(user_id)

    if not profile_data:
        flash('Recipient profile not found.', 'danger')
        return redirect(url_for('recipient.dashboard'))

    req = WigRequest.get_by_id(request_id)
    if not req:
        flash('Wig request record not found.', 'danger')
        return redirect(url_for('recipient.requests'))

    # Security check: Recipient can only track their own requests
    if req['recipient_id'] != profile_data['id']:
        flash("ACCESS DENIED: You cannot view or track another recipient's request.", 'danger')
        return render_template('errors/403.html', message="ACCESS DENIED: Unauthorized wig request access."), 403

    timeline = WigRequest.get_tracking_timeline(request_id)

    return render_template(
        'recipient/track.html',
        request_item=req,
        timeline=timeline,
        status_sequence=WigRequest.STATUS_SEQUENCE
    )
