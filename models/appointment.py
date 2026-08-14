"""
Appointment Model (Module 3)
Handles hair donation appointment scheduling, status tracking, donor and center validations,
and status transitions between Donors, NGOs, and Admins.
"""

from database.db import query_db, execute_db


class Appointment:
    VALID_STATUSES = ['Pending', 'Confirmed', 'Rejected', 'Cancelled', 'Completed', 'No Show']

    @staticmethod
    def create(donor_id, ngo_id, donation_center_id, appointment_date,
               appointment_time, purpose='Hair Donation', donor_notes=None):
        """
        Creates a new appointment booking for a donor at an approved NGO's donation center.
        """
        sql = """
            INSERT INTO appointments
            (donor_id, ngo_id, donation_center_id, appointment_date, appointment_time, purpose, donor_notes, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'Pending')
        """
        res = execute_db(sql, (
            donor_id,
            ngo_id,
            donation_center_id,
            str(appointment_date).strip(),
            str(appointment_time).strip(),
            str(purpose).strip() if purpose else 'Hair Donation',
            str(donor_notes).strip() if donor_notes else None
        ))
        return res['lastrowid']

    @staticmethod
    def get_by_id(appointment_id):
        """Fetches appointment details joined with donor, center, and NGO information."""
        sql = """
            SELECT a.*,
                   u_donor.name as donor_name,
                   u_donor.email as donor_email,
                   dp.phone as donor_phone,
                   dp.district as donor_district,
                   dp.hair_length as donor_hair_length,
                   dp.hair_type as donor_hair_type,
                   dp.hair_condition as donor_hair_condition,
                   np.organization_name as ngo_name,
                   np.phone as ngo_phone,
                   np.email as ngo_email,
                   dc.center_name,
                   dc.address as center_address,
                   dc.district as center_district,
                   dc.city as center_city,
                   dc.phone as center_phone,
                   dc.opening_time,
                   dc.closing_time,
                   dc.working_days
            FROM appointments a
            JOIN donor_profiles dp ON a.donor_id = dp.id
            JOIN users u_donor ON dp.user_id = u_donor.id
            JOIN ngo_profiles np ON a.ngo_id = np.id
            JOIN donation_centers dc ON a.donation_center_id = dc.id
            WHERE a.id = %s
        """
        return query_db(sql, (appointment_id,), one=True)

    @staticmethod
    def get_by_donor(donor_id, status=None):
        """Fetches all appointments booked by a specific donor."""
        params = [donor_id]
        sql = """
            SELECT a.*,
                   np.organization_name as ngo_name,
                   dc.center_name,
                   dc.address as center_address,
                   dc.city as center_city,
                   dc.district as center_district,
                   dc.phone as center_phone
            FROM appointments a
            JOIN ngo_profiles np ON a.ngo_id = np.id
            JOIN donation_centers dc ON a.donation_center_id = dc.id
            WHERE a.donor_id = %s
        """
        if status:
            sql += " AND a.status = %s"
            params.append(status)
        sql += " ORDER BY a.appointment_date DESC, a.appointment_time DESC"
        return query_db(sql, tuple(params))

    @staticmethod
    def get_by_ngo(ngo_id, status=None):
        """Fetches all appointments for an NGO's centers."""
        params = [ngo_id]
        sql = """
            SELECT a.*,
                   u_donor.name as donor_name,
                   u_donor.email as donor_email,
                   dp.phone as donor_phone,
                   dp.hair_length as donor_hair_length,
                   dp.hair_type as donor_hair_type,
                   dc.center_name,
                   dc.city as center_city
            FROM appointments a
            JOIN donor_profiles dp ON a.donor_id = dp.id
            JOIN users u_donor ON dp.user_id = u_donor.id
            JOIN donation_centers dc ON a.donation_center_id = dc.id
            WHERE a.ngo_id = %s
        """
        if status:
            sql += " AND a.status = %s"
            params.append(status)
        sql += " ORDER BY a.appointment_date DESC, a.appointment_time DESC"
        return query_db(sql, tuple(params))

    @staticmethod
    def get_all(status=None, district=None):
        """Fetches platform-wide appointments for Admin oversight."""
        params = []
        sql = """
            SELECT a.*,
                   u_donor.name as donor_name,
                   u_donor.email as donor_email,
                   np.organization_name as ngo_name,
                   dc.center_name,
                   dc.district as center_district,
                   dc.city as center_city
            FROM appointments a
            JOIN donor_profiles dp ON a.donor_id = dp.id
            JOIN users u_donor ON dp.user_id = u_donor.id
            JOIN ngo_profiles np ON a.ngo_id = np.id
            JOIN donation_centers dc ON a.donation_center_id = dc.id
            WHERE 1=1
        """
        if status:
            sql += " AND a.status = %s"
            params.append(status)
        if district:
            sql += " AND dc.district = %s"
            params.append(district)
        sql += " ORDER BY a.appointment_date DESC, a.appointment_time DESC"
        return query_db(sql, tuple(params) if params else None)

    @classmethod
    def update_status(cls, appointment_id, new_status, ngo_notes=None):
        """Updates appointment status and optional NGO notes."""
        if new_status not in cls.VALID_STATUSES:
            raise ValueError(f"Invalid appointment status: {new_status}")

        if ngo_notes is not None:
            sql = """
                UPDATE appointments
                SET status = %s,
                    ngo_notes = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """
            res = execute_db(sql, (new_status, str(ngo_notes).strip(), appointment_id))
        else:
            sql = """
                UPDATE appointments
                SET status = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """
            res = execute_db(sql, (new_status, appointment_id))
        return res['rowcount'] > 0

    @classmethod
    def cancel_by_donor(cls, appointment_id, donor_id, reason=None):
        """Allows donor to cancel their appointment if it is currently Pending or Confirmed."""
        appt = cls.get_by_id(appointment_id)
        if not appt:
            return False, "Appointment not found."
        if appt['donor_id'] != donor_id:
            return False, "Unauthorized to cancel this appointment."
        if appt['status'] not in ('Pending', 'Confirmed'):
            return False, f"Cannot cancel an appointment with status '{appt['status']}'."

        notes = appt['donor_notes'] or ''
        if reason:
            notes = (notes + f"\n[Donor Cancellation Reason: {reason}]").strip()

        sql = """
            UPDATE appointments
            SET status = 'Cancelled',
                donor_notes = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """
        execute_db(sql, (notes, appointment_id))
        return True, "Appointment cancelled successfully."

    @staticmethod
    def count_by_ngo(ngo_id):
        """Returns appointment summary statistics for an NGO dashboard."""
        sql = """
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'Pending' THEN 1 ELSE 0 END) as pending,
                SUM(CASE WHEN status = 'Confirmed' THEN 1 ELSE 0 END) as confirmed,
                SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN status = 'Cancelled' THEN 1 ELSE 0 END) as cancelled
            FROM appointments
            WHERE ngo_id = %s
        """
        res = query_db(sql, (ngo_id,), one=True)
        return {
            'total': res['total'] if res and res['total'] else 0,
            'pending': res['pending'] if res and res['pending'] else 0,
            'confirmed': res['confirmed'] if res and res['confirmed'] else 0,
            'completed': res['completed'] if res and res['completed'] else 0,
            'cancelled': res['cancelled'] if res and res['cancelled'] else 0,
        }

    @staticmethod
    def count_all():
        """Returns platform-wide appointment statistics for Admin dashboard."""
        sql = """
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'Pending' THEN 1 ELSE 0 END) as pending,
                SUM(CASE WHEN status = 'Confirmed' THEN 1 ELSE 0 END) as confirmed,
                SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) as completed
            FROM appointments
        """
        res = query_db(sql, one=True)
        return {
            'total': res['total'] if res and res['total'] else 0,
            'pending': res['pending'] if res and res['pending'] else 0,
            'confirmed': res['confirmed'] if res and res['confirmed'] else 0,
            'completed': res['completed'] if res and res['completed'] else 0,
        }
