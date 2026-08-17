"""
Admin Routes (Module 1 & Module 2)
Handles administrative dashboard, NGO approval/rejection workflows,
system user management, and platform-wide donation center oversight.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from routes.auth import role_required
from models.user import User
from models.ngo import NGO
from models.donor import Donor
from models.recipient import Recipient
from models.donation_center import DonationCenter
from models.appointment import Appointment
from models.donation import Donation

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route('/dashboard')
@role_required('admin')
def dashboard():
    """Admin centralized metrics, pending NGO review queue, donation center stats, and recent users."""
    role_counts = User.get_role_counts()
    pending_ngo_count = NGO.get_pending_count()
    pending_ngos = NGO.get_all(approval_status='pending')
    approved_ngos = NGO.get_all(approval_status='approved')
    recent_users = User.get_all()[:8]

    # Module 2 Metrics
    center_counts = DonationCenter.get_counts()
    recent_centers = DonationCenter.get_all()[:5]

    # Module 3 Metrics
    appt_counts = Appointment.count_all()
    don_counts = Donation.count_all()

    return render_template(
        'admin/dashboard.html',
        counts=role_counts,
        pending_ngo_count=pending_ngo_count,
        approved_ngo_count=len(approved_ngos),
        total_ngo_count=NGO.count(),
        pending_ngos=pending_ngos,
        recent_users=recent_users,
        center_counts=center_counts,
        recent_centers=recent_centers,
        appt_counts=appt_counts,
        don_counts=don_counts
    )


@admin_bp.route('/ngos')
@role_required('admin')
def ngos():
    """Manage NGOs, view attached donation center tallies, and filter by approval status."""
    status_filter = request.args.get('status', 'all').lower()
    if status_filter in ['pending', 'approved', 'rejected']:
        ngo_list = NGO.get_with_center_counts(approval_status=status_filter)
    else:
        status_filter = 'all'
        ngo_list = NGO.get_with_center_counts()

    return render_template(
        'admin/ngos.html',
        ngos=ngo_list,
        status_filter=status_filter,
        pending_count=NGO.get_pending_count()
    )



@admin_bp.route('/ngos/<int:ngo_id>/approve', methods=['POST'])
@role_required('admin')
def approve_ngo(ngo_id):
    """Approve a pending NGO registration."""
    ngo = NGO.get_by_id(ngo_id)
    if not ngo:
        flash('NGO record not found.', 'danger')
        return redirect(url_for('admin.ngos'))

    NGO.update_approval_status(ngo_id, 'approved')
    flash(f"NGO '{ngo['organization_name']}' has been officially approved! They now have full platform access.", 'success')
    return redirect(request.referrer or url_for('admin.ngos'))


@admin_bp.route('/ngos/<int:ngo_id>/reject', methods=['POST'])
@role_required('admin')
def reject_ngo(ngo_id):
    """Reject an NGO registration."""
    ngo = NGO.get_by_id(ngo_id)
    if not ngo:
        flash('NGO record not found.', 'danger')
        return redirect(url_for('admin.ngos'))

    NGO.update_approval_status(ngo_id, 'rejected')
    flash(f"NGO '{ngo['organization_name']}' registration has been rejected.", 'warning')
    return redirect(request.referrer or url_for('admin.ngos'))


@admin_bp.route('/users')
@role_required('admin')
def users():
    """View and manage system users."""
    role_filter = request.args.get('role', 'all').lower()
    if role_filter in ['donor', 'ngo', 'recipient', 'admin']:
        user_list = User.get_all(role=role_filter)
    else:
        role_filter = 'all'
        user_list = User.get_all()

    return render_template(
        'admin/users.html',
        users=user_list,
        role_filter=role_filter
    )


@admin_bp.route('/users/<int:user_id>/toggle-status', methods=['POST'])
@role_required('admin')
def toggle_user_status(user_id):
    """Toggle user active / inactive status."""
    # Prevent admin from deactivating their own account
    if user_id == session.get('user_id'):
        flash('You cannot deactivate your own administrative account.', 'danger')
        return redirect(request.referrer or url_for('admin.users'))

    user = User.get_by_id(user_id)
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('admin.users'))

    new_status = 'inactive' if user['status'] == 'active' else 'active'
    User.update_status(user_id, new_status)
    flash(f"Account for {user['name']} has been marked as {new_status}.", 'info')
    return redirect(request.referrer or url_for('admin.users'))


@admin_bp.route('/donors')
@role_required('admin')
def donors():
    """View all registered donors and their hair profiles."""
    all_donors = Donor.get_all()
    return render_template('admin/donors.html', donors=all_donors)


@admin_bp.route('/recipients')
@role_required('admin')
def recipients():
    """View all registered wig recipients."""
    all_recipients = Recipient.get_all()
    return render_template('admin/recipients.html', recipients=all_recipients)


# ==========================================================
# MODULE 2: DONATION CENTER ADMINISTRATIVE MANAGEMENT
# ==========================================================

@admin_bp.route('/donation-centers')
@role_required('admin')
def donation_centers():
    """Admin overview of all donation centers across all NGOs with filtering and search."""
    status_filter = request.args.get('status', 'all').strip()
    district_filter = request.args.get('district', 'all').strip()
    search_query = request.args.get('q', '').strip()

    centers = DonationCenter.get_all(
        status=status_filter if status_filter.lower() != 'all' else None,
        district=district_filter if district_filter.lower() != 'all' else None,
        search=search_query if search_query else None
    )
    counts = DonationCenter.get_counts()
    districts = DonationCenter.get_distinct_districts()

    return render_template(
        'admin/donation_centers.html',
        centers=centers,
        counts=counts,
        districts=districts,
        status_filter=status_filter,
        district_filter=district_filter,
        search_query=search_query
    )


@admin_bp.route('/donation-centers/<int:center_id>/toggle-status', methods=['POST'])
@role_required('admin')
def toggle_center_status(center_id):
    """Toggle center Active / Inactive status."""
    center = DonationCenter.get_by_id(center_id)
    if not center:
        flash('Donation center not found.', 'danger')
        return redirect(url_for('admin.donation_centers'))

    new_status = 'Inactive' if center['status'] == 'Active' else 'Active'
    DonationCenter.update_status(center_id, new_status)
    flash(f"Center '{center['center_name']}' status has been set to {new_status}.", 'info')
    return redirect(request.referrer or url_for('admin.donation_centers'))


@admin_bp.route('/donation-centers/<int:center_id>/status', methods=['POST'])
@role_required('admin')
def set_center_status(center_id):
    """Set specific center approval or operational status (Active, Inactive, Approved, Rejected, Pending)."""
    center = DonationCenter.get_by_id(center_id)
    if not center:
        flash('Donation center not found.', 'danger')
        return redirect(url_for('admin.donation_centers'))

    new_status = request.form.get('status', '').strip()
    if new_status in ['Active', 'Inactive', 'Approved', 'Rejected', 'Pending']:
        DonationCenter.update_status(center_id, new_status)
        flash(f"Center '{center['center_name']}' status updated to {new_status}.", 'success')
    else:
        flash('Invalid status provided.', 'danger')

    return redirect(request.referrer or url_for('admin.donation_centers'))


@admin_bp.route('/donation-centers/<int:center_id>')
@role_required('admin')
def view_center(center_id):
    """View full donation center details for administrative audit."""
    center = DonationCenter.get_by_id(center_id)
    if not center:
        flash('Donation center not found.', 'danger')
        return redirect(url_for('admin.donation_centers'))

    return render_template('ngo/donation_centers/view.html', center=center, is_admin=True)


# ==========================================================
# MODULE 3: ADMIN APPOINTMENTS & DONATIONS MONITORING
# ==========================================================

@admin_bp.route('/appointments')
@role_required('admin')
def appointments():
    """Platform-wide hair donation appointment monitoring and filtering."""
    status_filter = request.args.get('status', 'all').strip()
    district_filter = request.args.get('district', 'all').strip()

    if status_filter not in ['Pending', 'Confirmed', 'Completed', 'Cancelled', 'Rejected', 'No Show']:
        status_filter = 'all'
    if district_filter.lower() == 'all':
        district_filter = None

    appts = Appointment.get_all(
        status=status_filter if status_filter != 'all' else None,
        district=district_filter
    )
    counts = Appointment.count_all()
    districts = DonationCenter.get_distinct_districts()

    return render_template(
        'admin/appointments.html',
        appointments=appts,
        status_filter=status_filter,
        district_filter=district_filter or 'all',
        districts=districts,
        counts=counts
    )


@admin_bp.route('/donations')
@role_required('admin')
def donations():
    """Platform-wide completed hair donation ledger and impact audit."""
    district_filter = request.args.get('district', 'all').strip()
    if district_filter.lower() == 'all':
        district_filter = None

    donation_list = Donation.get_all(district=district_filter)
    stats = Donation.count_all()
    districts = DonationCenter.get_distinct_districts()

    return render_template(
        'admin/donations.html',
        donations=donation_list,
        stats=stats,
        district_filter=district_filter or 'all',
        districts=districts
    )


