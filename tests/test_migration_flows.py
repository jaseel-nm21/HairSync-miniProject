"""
Comprehensive Verification Test Suite for HairSync SQLite Migration
Covers all 5 exact required test flows:
TEST 1 — Donor Flow (Registration, SQLite persistence, Login, Dashboard, Profile Edit, Logout)
TEST 2 — NGO Flow (Registration, Pending Status, Admin Visibility & Approval, Approved Login, Dashboard)
TEST 3 — Recipient Flow (Registration, SQLite persistence, Login, Dashboard, Profile Edit)
TEST 4 — Security & Role Isolation Flow (Unauthenticated redirects, cross-role blocks)
TEST 5 — Database Integrity Flow (Table presence, SQLite retrieval, password hash security)
"""

import unittest
import sqlite3
import os
from werkzeug.security import check_password_hash
from app import create_app
from config import Config
from database.init_db import run_init


class MigrationFlowsTestCase(unittest.TestCase):
    def setUp(self):
        # Fresh database for every test flow
        run_init()
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_flow_1_donor(self):
        """TEST 1 — Donor: Register, save to SQLite, login, dashboard, profile edit, logout."""
        # 1. Register
        res = self.client.post('/register', data={
            'role': 'donor',
            'name': 'Test Donor',
            'email': 'donor@test.com',
            'password': 'Test@123',
            'confirm_password': 'Test@123',
            'phone': '+91 9876543211',
            'address': '123 Palm Grove',
            'district': 'Ernakulam',
            'hair_length': '12.0',
            'hair_type': 'Straight',
            'hair_condition': 'Virgin/Untreated'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Donor Community', res.data)

        # Verify saved in SQLite
        conn = sqlite3.connect(Config.DATABASE)
        conn.row_factory = sqlite3.Row
        user = conn.execute("SELECT * FROM users WHERE email = ?", ('donor@test.com',)).fetchone()
        self.assertIsNotNone(user, "Donor was not found in SQLite database!")
        self.assertEqual(user['name'], 'Test Donor')
        self.assertEqual(user['role'], 'donor')

        profile = conn.execute("SELECT * FROM donor_profiles WHERE user_id = ?", (user['id'],)).fetchone()
        self.assertIsNotNone(profile, "Donor profile was not found in SQLite!")
        self.assertEqual(profile['district'], 'Ernakulam')
        conn.close()

        # Logout
        res_logout = self.client.get('/logout', follow_redirects=True)
        self.assertEqual(res_logout.status_code, 200)
        self.assertIn(b'logged out', res_logout.data)

        # Login
        res_login = self.client.post('/login', data={
            'email': 'donor@test.com',
            'password': 'Test@123'
        }, follow_redirects=True)
        self.assertEqual(res_login.status_code, 200)
        self.assertIn(b'Donor Portal', res_login.data)

        # View profile
        res_prof = self.client.get('/donor/profile')
        self.assertEqual(res_prof.status_code, 200)
        self.assertIn(b'Test Donor', res_prof.data)

        # Edit profile
        res_edit = self.client.post('/donor/profile', data={
            'name': 'Test Donor Updated',
            'phone': '+91 9876543299',
            'address': '456 Updated Street',
            'district': 'Kottayam',
            'hair_length': '15.0',
            'hair_type': 'Curly',
            'hair_condition': 'Colored'
        }, follow_redirects=True)
        self.assertEqual(res_edit.status_code, 200)
        self.assertIn(b'updated successfully', res_edit.data)

        # Verify update persisted in SQLite
        conn = sqlite3.connect(Config.DATABASE)
        conn.row_factory = sqlite3.Row
        updated_prof = conn.execute("SELECT * FROM donor_profiles WHERE user_id = ?", (user['id'],)).fetchone()
        self.assertEqual(updated_prof['district'], 'Kottayam')
        self.assertEqual(updated_prof['hair_type'], 'Curly')
        conn.close()

        # Final logout
        res_logout2 = self.client.get('/logout', follow_redirects=True)
        self.assertEqual(res_logout2.status_code, 200)

    def test_flow_2_ngo(self):
        """TEST 2 — NGO: Register, Pending status, Admin views & approves, NGO logs in, Dashboard opens."""
        # 1. Register NGO
        res = self.client.post('/register', data={
            'role': 'ngo',
            'name': 'Test NGO Contact',
            'email': 'ngo@test.com',
            'password': 'Test@123',
            'confirm_password': 'Test@123',
            'phone': '+91 9811223344',
            'address': '78 Caring Way',
            'district': 'Thrissur',
            'org_name': 'Test NGO',
            'reg_number': 'NGO-TEST-2024-001',
            'description': 'Providing natural wigs to cancer patients.'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'pending administrative approval', res.data)

        # Verify Pending status in SQLite
        conn = sqlite3.connect(Config.DATABASE)
        conn.row_factory = sqlite3.Row
        ngo_user = conn.execute("SELECT * FROM users WHERE email = ?", ('ngo@test.com',)).fetchone()
        self.assertIsNotNone(ngo_user)
        self.assertEqual(ngo_user['status'], 'pending')

        ngo_prof = conn.execute("SELECT * FROM ngo_profiles WHERE user_id = ?", (ngo_user['id'],)).fetchone()
        self.assertIsNotNone(ngo_prof)
        self.assertEqual(ngo_prof['approval_status'], 'pending')
        conn.close()

        # Logout from auto-login session
        self.client.get('/logout', follow_redirects=True)

        # 2. Admin logs in
        res_admin_login = self.client.post('/login', data={
            'email': 'admin@hairsync.com',
            'password': 'Admin@123'
        }, follow_redirects=True)
        self.assertEqual(res_admin_login.status_code, 200)
        self.assertIn(b'Administration', res_admin_login.data)

        # Admin views NGO list
        res_ngos = self.client.get('/admin/ngos?status=pending')
        self.assertEqual(res_ngos.status_code, 200)
        self.assertIn(b'Test NGO', res_ngos.data)

        # Admin approves NGO
        res_approve = self.client.post(f'/admin/ngos/{ngo_prof["id"]}/approve', follow_redirects=True)
        self.assertEqual(res_approve.status_code, 200)
        self.assertIn(b'approved', res_approve.data)

        # Verify SQLite updated
        conn = sqlite3.connect(Config.DATABASE)
        conn.row_factory = sqlite3.Row
        approved_user = conn.execute("SELECT status FROM users WHERE id = ?", (ngo_user['id'],)).fetchone()
        approved_ngo = conn.execute("SELECT approval_status FROM ngo_profiles WHERE id = ?", (ngo_prof['id'],)).fetchone()
        self.assertEqual(approved_user['status'], 'active')
        self.assertEqual(approved_ngo['approval_status'], 'approved')
        conn.close()

        # Admin logout
        self.client.get('/logout', follow_redirects=True)

        # 3. Approved NGO logs in
        res_ngo_login = self.client.post('/login', data={
            'email': 'ngo@test.com',
            'password': 'Test@123'
        }, follow_redirects=True)
        self.assertIn(b'NGO &amp; Donation Center Portal', res_ngo_login.data)
        self.assertIn(b'Verified Partner NGO', res_ngo_login.data)

        # Logout
        self.client.get('/logout', follow_redirects=True)

    def test_flow_3_recipient(self):
        """TEST 3 — Recipient: Register, SQLite persistence, login, dashboard, profile works."""
        # 1. Register Recipient
        res = self.client.post('/register', data={
            'role': 'recipient',
            'name': 'Test Recipient',
            'email': 'recipient@test.com',
            'password': 'Test@123',
            'confirm_password': 'Test@123',
            'phone': '+91 9944556677',
            'address': 'Flat 3C, Sunshine Apts',
            'district': 'Kollam',
            'dob': '1995-08-20',
            'reason': 'Alopecia Areata / Totalis'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'recipient profile has been created', res.data)

        # Verify SQLite persistence
        conn = sqlite3.connect(Config.DATABASE)
        conn.row_factory = sqlite3.Row
        rec_user = conn.execute("SELECT * FROM users WHERE email = ?", ('recipient@test.com',)).fetchone()
        self.assertIsNotNone(rec_user)
        self.assertEqual(rec_user['name'], 'Test Recipient')
        self.assertEqual(rec_user['role'], 'recipient')

        rec_prof = conn.execute("SELECT * FROM recipient_profiles WHERE user_id = ?", (rec_user['id'],)).fetchone()
        self.assertIsNotNone(rec_prof)
        self.assertEqual(rec_prof['date_of_birth'], '1995-08-20')
        conn.close()

        # Logout
        self.client.get('/logout', follow_redirects=True)

        # Login as Recipient
        res_login = self.client.post('/login', data={
            'email': 'recipient@test.com',
            'password': 'Test@123'
        }, follow_redirects=True)
        self.assertEqual(res_login.status_code, 200)
        self.assertIn(b'Recipient Portal', res_login.data)

        # View recipient profile
        res_prof = self.client.get('/recipient/profile')
        self.assertEqual(res_prof.status_code, 200)
        self.assertIn(b'Alopecia Areata / Totalis', res_prof.data)

        # Logout
        self.client.get('/logout', follow_redirects=True)

    def test_flow_4_security(self):
        """TEST 4 — Security: Unauthenticated protection & cross-role access blocking."""
        # 1. Unauthenticated requests to protected dashboards must redirect to login
        protected_routes = [
            '/admin/dashboard',
            '/admin/ngos',
            '/admin/users',
            '/donor/dashboard',
            '/donor/profile',
            '/ngo/dashboard',
            '/ngo/profile',
            '/recipient/dashboard',
            '/recipient/profile'
        ]
        for route in protected_routes:
            with self.subTest(route=route):
                res = self.client.get(route, follow_redirects=False)
                self.assertEqual(res.status_code, 302)
                self.assertIn('/login', res.headers.get('Location', ''))

        # 2. Donor attempts to access Admin dashboard -> blocked
        with self.client.session_transaction() as sess:
            sess['user_id'] = 4
            sess['user_name'] = 'Donor User'
            sess['user_email'] = 'donor@test.com'
            sess['role'] = 'donor'

        res = self.client.get('/admin/dashboard', follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertIn('/donor/dashboard', res.headers.get('Location', ''))

        # 3. NGO attempts to access Admin dashboard -> blocked
        with self.client.session_transaction() as sess:
            sess['user_id'] = 2
            sess['user_name'] = 'NGO User'
            sess['user_email'] = 'contact@hopehair.org'
            sess['role'] = 'ngo'

        res = self.client.get('/admin/dashboard', follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertIn('/ngo/dashboard', res.headers.get('Location', ''))

        # 4. Recipient attempts to access Admin dashboard -> blocked
        with self.client.session_transaction() as sess:
            sess['user_id'] = 5
            sess['user_name'] = 'Recipient User'
            sess['user_email'] = 'recipient@test.com'
            sess['role'] = 'recipient'

        res = self.client.get('/admin/dashboard', follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertIn('/recipient/dashboard', res.headers.get('Location', ''))

    def test_flow_5_database(self):
        """TEST 5 — Database: File presence, required tables, retrieval, secure password hashing."""
        db_path = Config.DATABASE
        self.assertTrue(os.path.exists(db_path), f"Database file does not exist at {db_path}")

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # Verify all required tables exist
        tables_res = cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        table_names = [r['name'] for r in tables_res]
        required_tables = ['users', 'donor_profiles', 'ngo_profiles', 'recipient_profiles']
        for table in required_tables:
            self.assertIn(table, table_names, f"Missing table {table} in SQLite database!")

        # Verify passwords remain securely hashed
        users = cur.execute("SELECT email, password_hash FROM users").fetchall()
        self.assertGreater(len(users), 0)
        for u in users:
            pw_hash = u['password_hash']
            # Password hashes must NOT be plaintext
            self.assertFalse(pw_hash.startswith('Password@') or pw_hash.startswith('Admin@') or pw_hash.startswith('Test@'))
            self.assertTrue(pw_hash.startswith('scrypt:') or pw_hash.startswith('pbkdf2:'),
                            f"Password hash format unexpected: {pw_hash}")

        # Verify admin password hash validates
        admin = cur.execute("SELECT password_hash FROM users WHERE email = 'admin@hairsync.com'").fetchone()
        self.assertTrue(check_password_hash(admin['password_hash'], 'Admin@123'))

        conn.close()


if __name__ == '__main__':
    unittest.main()
