"""
User Model
Handles user authentication, account creation, and user queries.
"""

from werkzeug.security import generate_password_hash, check_password_hash
from database.db import query_db, execute_db


class User:
    @staticmethod
    def create(name, email, password, role, status='active'):
        """
        Creates a new user with hashed password.
        Returns the created user's ID.
        """
        password_hash = generate_password_hash(password)
        sql = """
            INSERT INTO users (name, email, password_hash, role, status)
            VALUES (%s, %s, %s, %s, %s)
        """
        res = execute_db(sql, (name.strip(), email.strip().lower(), password_hash, role, status))
        return res['lastrowid']

    @staticmethod
    def get_by_id(user_id):
        """Fetch a user by primary key ID."""
        sql = "SELECT id, name, email, password_hash, role, status, created_at, updated_at FROM users WHERE id = %s"
        return query_db(sql, (user_id,), one=True)

    @staticmethod
    def get_by_email(email):
        """Fetch a user by email address."""
        sql = "SELECT id, name, email, password_hash, role, status, created_at, updated_at FROM users WHERE email = %s"
        return query_db(sql, (email.strip().lower(),), one=True)

    @staticmethod
    def verify_password(password_hash, password):
        """Validates a plain-text password against the stored hash."""
        if not password_hash or not password:
            return False
        return check_password_hash(password_hash, password)

    @staticmethod
    def update_password(user_id, new_password):
        """Update user password with fresh hash."""
        password_hash = generate_password_hash(new_password)
        sql = "UPDATE users SET password_hash = %s WHERE id = %s"
        return execute_db(sql, (password_hash, user_id))

    @staticmethod
    def update_name_email(user_id, name, email):
        """Update user's display name and email."""
        sql = "UPDATE users SET name = %s, email = %s WHERE id = %s"
        return execute_db(sql, (name.strip(), email.strip().lower(), user_id))

    @staticmethod
    def update_status(user_id, status):
        """Update account status (active, inactive, pending, suspended)."""
        sql = "UPDATE users SET status = %s WHERE id = %s"
        return execute_db(sql, (status, user_id))

    @staticmethod
    def get_all(role=None):
        """Fetch all users, optionally filtered by role."""
        if role:
            sql = "SELECT id, name, email, role, status, created_at FROM users WHERE role = %s ORDER BY created_at DESC"
            return query_db(sql, (role,))
        else:
            sql = "SELECT id, name, email, role, status, created_at FROM users ORDER BY created_at DESC"
            return query_db(sql)

    @staticmethod
    def get_role_counts():
        """Returns count of users grouped by role for admin analytics."""
        sql = """
            SELECT role, COUNT(*) as count 
            FROM users 
            GROUP BY role
        """
        rows = query_db(sql)
        counts = {'admin': 0, 'ngo': 0, 'donor': 0, 'recipient': 0, 'total': 0}
        for row in rows:
            role = row['role']
            counts[role] = row['count']
            counts['total'] += row['count']
        return counts
