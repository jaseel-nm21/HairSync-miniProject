"""
Recipient Routes
Handles Recipient dashboard, medical/hair loss reason profile, and future wig request tracking hooks.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from routes.auth import role_required
from models.user import User
from models.recipient import Recipient

recipient_bp = Blueprint('recipient', __name__, url_prefix='/recipient')


@recipient_bp.route('/dashboard')
@role_required('recipient')
def dashboard():
    """Recipient dashboard showing application overview and future wig request access."""
    user_id = session.get('user_id')
    user = User.get_by_id(user_id)
    profile = Recipient.get_by_user_id(user_id)

    return render_template(
        'recipient/dashboard.html',
        user=user,
        profile=profile
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
