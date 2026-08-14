"""
Donor Model
Handles donor profile creation, updates, and lookups.
"""

from database.db import query_db, execute_db


class Donor:
    @staticmethod
    def get_by_user_id(user_id):
        """Fetch donor profile with user account details."""
        sql = """
            SELECT d.*, u.name, u.email, u.status as user_status, u.created_at as user_joined
            FROM donor_profiles d
            JOIN users u ON d.user_id = u.id
            WHERE d.user_id = %s
        """
        return query_db(sql, (user_id,), one=True)

    @staticmethod
    def get_by_id(donor_id):
        """Fetch donor profile by donor ID."""
        sql = """
            SELECT d.*, u.name, u.email
            FROM donor_profiles d
            JOIN users u ON d.user_id = u.id
            WHERE d.id = %s
        """
        return query_db(sql, (donor_id,), one=True)

    @staticmethod
    def create(user_id, phone, address, district, hair_length=None, hair_type=None, hair_condition=None, photo=None):
        """Create new donor profile."""
        sql = """
            INSERT INTO donor_profiles 
            (user_id, phone, address, district, hair_length, hair_type, hair_condition, photo)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        res = execute_db(sql, (
            user_id,
            phone.strip(),
            address.strip(),
            district.strip(),
            float(hair_length) if hair_length else None,
            hair_type.strip() if hair_type else None,
            hair_condition.strip() if hair_condition else None,
            photo
        ))
        return res['lastrowid']

    @staticmethod
    def update(user_id, phone, address, district, hair_length=None, hair_type=None, hair_condition=None, photo=None):
        """Update existing donor profile."""
        if photo:
            sql = """
                UPDATE donor_profiles
                SET phone = %s, address = %s, district = %s, 
                    hair_length = %s, hair_type = %s, hair_condition = %s, photo = %s
                WHERE user_id = %s
            """
            return execute_db(sql, (
                phone.strip(),
                address.strip(),
                district.strip(),
                float(hair_length) if hair_length else None,
                hair_type.strip() if hair_type else None,
                hair_condition.strip() if hair_condition else None,
                photo,
                user_id
            ))
        else:
            sql = """
                UPDATE donor_profiles
                SET phone = %s, address = %s, district = %s, 
                    hair_length = %s, hair_type = %s, hair_condition = %s
                WHERE user_id = %s
            """
            return execute_db(sql, (
                phone.strip(),
                address.strip(),
                district.strip(),
                float(hair_length) if hair_length else None,
                hair_type.strip() if hair_type else None,
                hair_condition.strip() if hair_condition else None,
                user_id
            ))

    @staticmethod
    def create_or_update(user_id, phone, address, district, hair_length=None, hair_type=None, hair_condition=None, photo=None):
        """Convenience method to insert or update profile."""
        existing = Donor.get_by_user_id(user_id)
        if existing:
            Donor.update(user_id, phone, address, district, hair_length, hair_type, hair_condition, photo)
            return existing['id']
        else:
            return Donor.create(user_id, phone, address, district, hair_length, hair_type, hair_condition, photo)

    @staticmethod
    def get_all():
        """Retrieve all donor profiles with user names and contacts."""
        sql = """
            SELECT d.*, u.name, u.email, u.status as user_status
            FROM donor_profiles d
            JOIN users u ON d.user_id = u.id
            ORDER BY d.created_at DESC
        """
        return query_db(sql)

    @staticmethod
    def count():
        """Total donors count."""
        sql = "SELECT COUNT(*) as count FROM donor_profiles"
        res = query_db(sql, one=True)
        return res['count'] if res else 0
