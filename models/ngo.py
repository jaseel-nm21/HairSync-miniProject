"""
NGO Model
Handles NGO organization profile data, registration number verification,
and Admin approval/rejection workflows.
"""

from database.db import query_db, execute_db


class NGO:
    @staticmethod
    def get_by_user_id(user_id):
        """Fetch NGO profile with user account details."""
        sql = """
            SELECT n.*, u.name as account_holder, u.status as account_status, u.created_at as registered_on
            FROM ngo_profiles n
            JOIN users u ON n.user_id = u.id
            WHERE n.user_id = %s
        """
        return query_db(sql, (user_id,), one=True)

    @staticmethod
    def get_by_id(ngo_id):
        """Fetch NGO by profile ID."""
        sql = """
            SELECT n.*, u.name as account_holder, u.status as account_status, u.email as user_email
            FROM ngo_profiles n
            JOIN users u ON n.user_id = u.id
            WHERE n.id = %s
        """
        return query_db(sql, (ngo_id,), one=True)

    @staticmethod
    def get_by_reg_no(reg_no):
        """Find NGO profile by official government registration number."""
        sql = "SELECT * FROM ngo_profiles WHERE registration_number = %s"
        return query_db(sql, (reg_no.strip(),), one=True)

    @staticmethod
    def create(user_id, organization_name, registration_number, phone, email, address, district, description=None, approval_status='pending'):
        """Creates an NGO profile. Defaults to 'pending'."""
        sql = """
            INSERT INTO ngo_profiles 
            (user_id, organization_name, registration_number, phone, email, address, district, description, approval_status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        res = execute_db(sql, (
            user_id,
            organization_name.strip(),
            registration_number.strip(),
            phone.strip(),
            email.strip().lower(),
            address.strip(),
            district.strip(),
            description.strip() if description else None,
            approval_status
        ))
        return res['lastrowid']

    @staticmethod
    def update(user_id, organization_name, registration_number, phone, email, address, district, description=None):
        """Update NGO profile information."""
        sql = """
            UPDATE ngo_profiles
            SET organization_name = %s, registration_number = %s, phone = %s, 
                email = %s, address = %s, district = %s, description = %s
            WHERE user_id = %s
        """
        return execute_db(sql, (
            organization_name.strip(),
            registration_number.strip(),
            phone.strip(),
            email.strip().lower(),
            address.strip(),
            district.strip(),
            description.strip() if description else None,
            user_id
        ))

    @staticmethod
    def create_or_update(user_id, organization_name, registration_number, phone, email, address, district, description=None):
        """Convenience method to insert or update NGO profile."""
        existing = NGO.get_by_user_id(user_id)
        if existing:
            NGO.update(user_id, organization_name, registration_number, phone, email, address, district, description)
            return existing['id']
        else:
            return NGO.create(user_id, organization_name, registration_number, phone, email, address, district, description)

    @staticmethod
    def update_approval_status(ngo_id, status):
        """
        Admin action to approve or reject an NGO.
        Also synchronizes the user account status.
        """
        sql = "UPDATE ngo_profiles SET approval_status = %s WHERE id = %s"
        execute_db(sql, (status, ngo_id))

        # Synchronize user status: 'active' if approved, 'inactive' or 'pending' otherwise
        user_status = 'active' if status == 'approved' else ('pending' if status == 'pending' else 'inactive')
        sync_sql = """
            UPDATE users
            SET status = %s
            WHERE id = (SELECT user_id FROM ngo_profiles WHERE id = %s)
        """
        return execute_db(sync_sql, (user_status, ngo_id))

    @staticmethod
    def get_all(approval_status=None):
        """Get all NGOs, optionally filtered by approval status."""
        if approval_status:
            sql = """
                SELECT n.*, u.name as account_holder, u.email as user_email
                FROM ngo_profiles n
                JOIN users u ON n.user_id = u.id
                WHERE n.approval_status = %s
                ORDER BY n.created_at DESC
            """
            return query_db(sql, (approval_status,))
        else:
            sql = """
                SELECT n.*, u.name as account_holder, u.email as user_email
                FROM ngo_profiles n
                JOIN users u ON n.user_id = u.id
                ORDER BY n.created_at DESC
            """
            return query_db(sql)

    @staticmethod
    def get_pending_count():
        """Count of pending NGO applications awaiting Admin review."""
        sql = "SELECT COUNT(*) as count FROM ngo_profiles WHERE approval_status = 'pending'"
        res = query_db(sql, one=True)
        return res['count'] if res else 0

    @staticmethod
    def count():
        """Count of all NGOs."""
        sql = "SELECT COUNT(*) as count FROM ngo_profiles"
        res = query_db(sql, one=True)
        return res['count'] if res else 0

    @staticmethod
    def get_with_center_counts(approval_status=None):
        """Get all NGOs with their count of donation centers."""
        if approval_status:
            sql = """
                SELECT n.*, u.name as account_holder, u.email as user_email,
                       COUNT(dc.id) as center_count
                FROM ngo_profiles n
                JOIN users u ON n.user_id = u.id
                LEFT JOIN donation_centers dc ON dc.ngo_id = n.id
                WHERE n.approval_status = %s
                GROUP BY n.id
                ORDER BY n.created_at DESC
            """
            return query_db(sql, (approval_status,))
        else:
            sql = """
                SELECT n.*, u.name as account_holder, u.email as user_email,
                       COUNT(dc.id) as center_count
                FROM ngo_profiles n
                JOIN users u ON n.user_id = u.id
                LEFT JOIN donation_centers dc ON dc.ngo_id = n.id
                GROUP BY n.id
                ORDER BY n.created_at DESC
            """
            return query_db(sql)

    @staticmethod
    def get_centers(ngo_id):
        """Retrieve all donation centers owned by a given NGO profile ID."""
        sql = "SELECT * FROM donation_centers WHERE ngo_id = %s ORDER BY created_at DESC"
        return query_db(sql, (ngo_id,))

