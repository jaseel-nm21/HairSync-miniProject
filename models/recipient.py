"""
Recipient Model
Handles recipient medical/wig request profile data and management.
"""

from database.db import query_db, execute_db


class Recipient:
    @staticmethod
    def get_by_user_id(user_id):
        """Fetch recipient profile with user details."""
        sql = """
            SELECT r.*, u.name, u.email, u.status as user_status, u.created_at as joined_date
            FROM recipient_profiles r
            JOIN users u ON r.user_id = u.id
            WHERE r.user_id = %s
        """
        return query_db(sql, (user_id,), one=True)

    @staticmethod
    def get_by_id(recipient_id):
        """Fetch recipient by profile ID."""
        sql = """
            SELECT r.*, u.name, u.email
            FROM recipient_profiles r
            JOIN users u ON r.user_id = u.id
            WHERE r.id = %s
        """
        return query_db(sql, (recipient_id,), one=True)

    @staticmethod
    def create(user_id, phone, address, district, date_of_birth, reason_for_wig):
        """Create new recipient profile."""
        sql = """
            INSERT INTO recipient_profiles 
            (user_id, phone, address, district, date_of_birth, reason_for_wig)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        res = execute_db(sql, (
            user_id,
            phone.strip(),
            address.strip(),
            district.strip(),
            date_of_birth,
            reason_for_wig.strip()
        ))
        return res['lastrowid']

    @staticmethod
    def update(user_id, phone, address, district, date_of_birth, reason_for_wig):
        """Update existing recipient profile."""
        sql = """
            UPDATE recipient_profiles
            SET phone = %s, address = %s, district = %s, 
                date_of_birth = %s, reason_for_wig = %s
            WHERE user_id = %s
        """
        return execute_db(sql, (
            phone.strip(),
            address.strip(),
            district.strip(),
            date_of_birth,
            reason_for_wig.strip(),
            user_id
        ))

    @staticmethod
    def create_or_update(user_id, phone, address, district, date_of_birth, reason_for_wig):
        """Convenience method to insert or update recipient profile."""
        existing = Recipient.get_by_user_id(user_id)
        if existing:
            Recipient.update(user_id, phone, address, district, date_of_birth, reason_for_wig)
            return existing['id']
        else:
            return Recipient.create(user_id, phone, address, district, date_of_birth, reason_for_wig)

    @staticmethod
    def get_all():
        """Fetch all recipient profiles with user contact details."""
        sql = """
            SELECT r.*, u.name, u.email, u.status as user_status
            FROM recipient_profiles r
            JOIN users u ON r.user_id = u.id
            ORDER BY r.created_at DESC
        """
        return query_db(sql)

    @staticmethod
    def count():
        """Count total recipients."""
        sql = "SELECT COUNT(*) as count FROM recipient_profiles"
        res = query_db(sql, one=True)
        return res['count'] if res else 0
