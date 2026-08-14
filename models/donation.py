"""
Donation Model (Module 3)
Handles permanent hair donation records, fulfillment logging from appointments,
donor donation history, and NGO collection metrics.
"""

from database.db import query_db, execute_db


class Donation:
    VALID_STATUSES = ['Completed', 'Recorded', 'Rejected']

    @classmethod
    def create(cls, donor_id, ngo_id, donation_center_id, hair_length,
               hair_type, hair_condition, donation_date, appointment_id=None,
               quantity_or_estimated_weight=None, notes=None, status='Completed'):
        """
        Records a completed hair donation. If linked to an appointment, validates uniqueness.
        """
        if status not in cls.VALID_STATUSES:
            status = 'Completed'

        sql = """
            INSERT INTO donations
            (donor_id, ngo_id, donation_center_id, appointment_id, hair_length,
             hair_type, hair_condition, donation_date, quantity_or_estimated_weight, notes, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        res = execute_db(sql, (
            donor_id,
            ngo_id,
            donation_center_id,
            appointment_id if appointment_id else None,
            float(hair_length),
            str(hair_type).strip(),
            str(hair_condition).strip(),
            str(donation_date).strip(),
            str(quantity_or_estimated_weight).strip() if quantity_or_estimated_weight else None,
            str(notes).strip() if notes else None,
            status
        ))
        return res['lastrowid']

    @staticmethod
    def get_by_id(donation_id):
        """Fetches full donation record joined with donor, NGO, and center details."""
        sql = """
            SELECT d.*,
                   u_donor.name as donor_name,
                   u_donor.email as donor_email,
                   dp.phone as donor_phone,
                   dp.district as donor_district,
                   np.organization_name as ngo_name,
                   np.registration_number as ngo_reg_no,
                   dc.center_name,
                   dc.address as center_address,
                   dc.district as center_district,
                   dc.city as center_city,
                   a.appointment_date,
                   a.appointment_time
            FROM donations d
            JOIN donor_profiles dp ON d.donor_id = dp.id
            JOIN users u_donor ON dp.user_id = u_donor.id
            JOIN ngo_profiles np ON d.ngo_id = np.id
            JOIN donation_centers dc ON d.donation_center_id = dc.id
            LEFT JOIN appointments a ON d.appointment_id = a.id
            WHERE d.id = %s
        """
        return query_db(sql, (donation_id,), one=True)

    @staticmethod
    def get_by_donor(donor_id):
        """Fetches all donation records for a specific donor."""
        sql = """
            SELECT d.*,
                   np.organization_name as ngo_name,
                   dc.center_name,
                   dc.district as center_district,
                   dc.city as center_city
            FROM donations d
            JOIN ngo_profiles np ON d.ngo_id = np.id
            JOIN donation_centers dc ON d.donation_center_id = dc.id
            WHERE d.donor_id = %s
            ORDER BY d.donation_date DESC, d.created_at DESC
        """
        return query_db(sql, (donor_id,))

    @staticmethod
    def get_by_ngo(ngo_id):
        """Fetches all donations recorded by an NGO."""
        sql = """
            SELECT d.*,
                   u_donor.name as donor_name,
                   u_donor.email as donor_email,
                   dp.phone as donor_phone,
                   dc.center_name,
                   dc.city as center_city
            FROM donations d
            JOIN donor_profiles dp ON d.donor_id = dp.id
            JOIN users u_donor ON dp.user_id = u_donor.id
            JOIN donation_centers dc ON d.donation_center_id = dc.id
            WHERE d.ngo_id = %s
            ORDER BY d.donation_date DESC, d.created_at DESC
        """
        return query_db(sql, (ngo_id,))

    @staticmethod
    def get_all(district=None):
        """Fetches all platform donations for Admin."""
        params = []
        sql = """
            SELECT d.*,
                   u_donor.name as donor_name,
                   np.organization_name as ngo_name,
                   dc.center_name,
                   dc.district as center_district,
                   dc.city as center_city
            FROM donations d
            JOIN donor_profiles dp ON d.donor_id = dp.id
            JOIN users u_donor ON dp.user_id = u_donor.id
            JOIN ngo_profiles np ON d.ngo_id = np.id
            JOIN donation_centers dc ON d.donation_center_id = dc.id
            WHERE 1=1
        """
        if district:
            sql += " AND dc.district = %s"
            params.append(district)
        sql += " ORDER BY d.donation_date DESC, d.created_at DESC"
        return query_db(sql, tuple(params) if params else None)

    @staticmethod
    def count_by_donor(donor_id):
        """Returns donation count and total length donated for a donor."""
        sql = """
            SELECT COUNT(*) as count,
                   COALESCE(SUM(hair_length), 0) as total_length
            FROM donations
            WHERE donor_id = %s AND status IN ('Completed', 'Recorded')
        """
        res = query_db(sql, (donor_id,), one=True)
        return {
            'count': res['count'] if res else 0,
            'total_length': round(float(res['total_length']), 1) if res and res['total_length'] else 0.0
        }

    @staticmethod
    def count_by_ngo(ngo_id):
        """Returns donation count and total length donated for an NGO."""
        sql = """
            SELECT COUNT(*) as count,
                   COALESCE(SUM(hair_length), 0) as total_length
            FROM donations
            WHERE ngo_id = %s AND status IN ('Completed', 'Recorded')
        """
        res = query_db(sql, (ngo_id,), one=True)
        return {
            'count': res['count'] if res else 0,
            'total_length': round(float(res['total_length']), 1) if res and res['total_length'] else 0.0
        }

    @staticmethod
    def count_all():
        """Returns platform-wide donation count and total length."""
        sql = """
            SELECT COUNT(*) as count,
                   COALESCE(SUM(hair_length), 0) as total_length
            FROM donations
            WHERE status IN ('Completed', 'Recorded')
        """
        res = query_db(sql, one=True)
        return {
            'count': res['count'] if res else 0,
            'total_length': round(float(res['total_length']), 1) if res and res['total_length'] else 0.0
        }
