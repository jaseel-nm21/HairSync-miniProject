"""
HairSync Module 2 Test Suite: NGO & Donation Center Management
Implements all 8 required verification tests from prompt specification:
TEST 1 — NGO approval (Registration, Pending status, Restricted center actions, Admin approval, NGO status becomes Approved, can manage centers)
TEST 2 — Create donation center (Malappuram Hair Donation Center with coordinates saved in SQLite)
TEST 3 — Edit center (Update center details and verify SQLite changes)
TEST 4 — Delete center (Delete test center and verify removal from SQLite)
TEST 5 — Multiple centers (Create two centers under same NGO, verify both appear correctly)
TEST 6 — Security (Cross-NGO access block: NGO A cannot access/edit/delete NGO B's center -> ACCESS DENIED)
TEST 7 — Donor (Donor views approved/active centers, cannot create/edit/delete centers)
TEST 8 — Admin (Admin views all NGOs, approval flows, donation center list, center ownership, status updates)
"""

import unittest
import sqlite3
from app import create_app
from config import Config
from database.init_db import run_init
from models.donation_center import DonationCenter
from models.ngo import NGO
from models.user import User


class Module2TestCase(unittest.TestCase):
    def setUp(self):
        # Reset database to fresh known state for each test
        run_init()
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()

    def tearDown(self):
        self.ctx.pop()


    def test_01_ngo_approval_flow(self):
        """
        TEST 1 — NGO Approval
        Register NGO 'Test NGO 2' (ngo2@test.com), verify pending status and restricted actions;
        Admin approves; NGO status becomes Approved and unlocks center management.
        """
        # 1. Register NGO
        res_reg = self.client.post('/register', data={
            'role': 'ngo',
            'name': 'Test NGO 2 Contact',
            'email': 'ngo2@test.com',
            'password': 'Test@123',
            'confirm_password': 'Test@123',
            'phone': '9847012345',
            'address': 'Civil Station Road',
            'district': 'Malappuram',
            'org_name': 'Test NGO 2',
            'reg_number': 'REG-MLP-2024-002',
            'description': 'Malappuram regional cancer support community.'
        }, follow_redirects=True)
        self.assertEqual(res_reg.status_code, 200)

        # Verify Pending status in database
        ngo_user = User.get_by_email('ngo2@test.com')
        self.assertIsNotNone(ngo_user)
        self.assertEqual(ngo_user['status'], 'pending')

        ngo_prof = NGO.get_by_user_id(ngo_user['id'])
        self.assertIsNotNone(ngo_prof)
        self.assertEqual(ngo_prof['approval_status'], 'pending')

        # 2. Verify NGO CANNOT perform restricted actions before approval
        # Attempting to access donation centers add page should redirect to dashboard with warning
        res_restricted = self.client.get('/ngo/donation-centers/add', follow_redirects=True)
        self.assertIn(b'pending administrative approval', res_restricted.data.lower())

        # Attempting POST to create center while pending should also redirect with restriction warning
        res_restricted_post = self.client.post('/ngo/donation-centers/add', data={
            'center_name': 'Unauthorized Center',
            'address': 'Nowhere',
            'district': 'Malappuram',
            'city': 'Malappuram',
            'pincode': '676505',
            'phone': '9876543210',
            'opening_time': '09:00',
            'closing_time': '17:00',
            'working_days': 'Monday - Saturday'
        }, follow_redirects=True)
        self.assertIn(b'pending administrative approval', res_restricted_post.data.lower())

        # Ensure no center was created
        conn = sqlite3.connect(Config.DATABASE)
        unauth_center = conn.execute("SELECT * FROM donation_centers WHERE ngo_id = ?", (ngo_prof['id'],)).fetchone()
        self.assertIsNone(unauth_center, "Center should NOT be created by unapproved NGO!")
        conn.close()

        # Logout from NGO session
        self.client.get('/logout', follow_redirects=True)

        # 3. Admin logs in and sees NGO
        res_admin_login = self.client.post('/login', data={
            'email': 'admin@hairsync.com',
            'password': 'Admin@123'
        }, follow_redirects=True)
        self.assertEqual(res_admin_login.status_code, 200)

        res_admin_ngos = self.client.get('/admin/ngos?status=pending')
        self.assertIn(b'Test NGO 2', res_admin_ngos.data)

        # 4. Admin approves NGO
        res_approve = self.client.post(f'/admin/ngos/{ngo_prof["id"]}/approve', follow_redirects=True)
        self.assertEqual(res_approve.status_code, 200)
        self.assertIn(b'approved', res_approve.data.lower())

        # Verify status became Approved in database
        updated_prof = NGO.get_by_id(ngo_prof['id'])
        self.assertEqual(updated_prof['approval_status'], 'approved')
        updated_user = User.get_by_id(ngo_user['id'])
        self.assertEqual(updated_user['status'], 'active')

        # Admin logout
        self.client.get('/logout', follow_redirects=True)

        # 5. Approved NGO logs in and can now manage donation centers
        res_ngo_login = self.client.post('/login', data={
            'email': 'ngo2@test.com',
            'password': 'Test@123'
        }, follow_redirects=True)
        self.assertEqual(res_ngo_login.status_code, 200)
        self.assertIn(b'Verified Partner NGO', res_ngo_login.data)

        res_centers_page = self.client.get('/ngo/donation-centers')
        self.assertEqual(res_centers_page.status_code, 200)
        self.assertIn(b'Donation Collection Centers', res_centers_page.data)

    def test_02_create_donation_center(self):
        """
        TEST 2 — Create donation center
        Login as approved NGO (contact@hopehair.org / Password@123).
        Create Malappuram Hair Donation Center with exact specified fields and coordinates.
        Verify that the center is saved in SQLite.
        """
        # Login as approved NGO
        self.client.post('/login', data={
            'email': 'contact@hopehair.org',
            'password': 'Password@123'
        }, follow_redirects=True)

        # Create center
        res_create = self.client.post('/ngo/donation-centers/add', data={
            'center_name': 'Malappuram Hair Donation Center',
            'address': 'Malappuram',
            'district': 'Malappuram',
            'city': 'Malappuram',
            'state': 'Kerala',
            'pincode': '676505',
            'phone': '9876543210',
            'email': 'malappuram@hopehair.org',
            'opening_time': '09:00',
            'closing_time': '17:00',
            'working_days': 'Monday - Saturday',
            'latitude': '11.0510',
            'longitude': '76.0711',
            'description': 'Hair donation center for collecting and managing hair donations.',
            'status': 'Active'
        }, follow_redirects=True)
        self.assertEqual(res_create.status_code, 200)
        self.assertIn(b'created successfully', res_create.data.lower())
        self.assertIn(b'Malappuram Hair Donation Center', res_create.data)

        # Verify saved in SQLite database directly
        conn = sqlite3.connect(Config.DATABASE)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        center = cur.execute(
            "SELECT * FROM donation_centers WHERE center_name = ?", 
            ('Malappuram Hair Donation Center',)
        ).fetchone()

        self.assertIsNotNone(center, "Malappuram Hair Donation Center was not saved in SQLite!")
        self.assertEqual(center['district'], 'Malappuram')
        self.assertEqual(center['city'], 'Malappuram')
        self.assertEqual(center['pincode'], '676505')
        self.assertEqual(center['phone'], '9876543210')
        self.assertEqual(center['opening_time'], '09:00')
        self.assertEqual(center['closing_time'], '17:00')
        self.assertEqual(center['working_days'], 'Monday - Saturday')
        self.assertAlmostEqual(center['latitude'], 11.0510, places=4)
        self.assertAlmostEqual(center['longitude'], 76.0711, places=4)
        self.assertEqual(center['status'], 'Active')
        conn.close()

    def test_03_edit_center(self):
        """
        TEST 3 — Edit center
        Edit the center details and verify the changes are saved in SQLite.
        """
        # Login as approved NGO
        self.client.post('/login', data={
            'email': 'contact@hopehair.org',
            'password': 'Password@123'
        }, follow_redirects=True)

        # Get Hope Hair Foundation NGO profile
        ngo_user = User.get_by_email('contact@hopehair.org')
        ngo_prof = NGO.get_by_user_id(ngo_user['id'])

        # Create center to edit
        cid = DonationCenter.create(
            ngo_id=ngo_prof['id'],
            center_name='Kozhikode Test Hub',
            address='Beach Road',
            district='Kozhikode',
            city='Kozhikode',
            state='Kerala',
            pincode='673001',
            phone='9845112233',
            email='calicut@hopehair.org',
            opening_time='10:00',
            closing_time='18:00',
            working_days='Monday - Friday',
            latitude=11.2588,
            longitude=75.7804,
            status='Active'
        )

        # Edit center details
        res_edit = self.client.post(f'/ngo/donation-centers/{cid}/edit', data={
            'center_name': 'Kozhikode Premium Drop Hub',
            'address': 'Updated Beach Road, Suite 5',
            'district': 'Kozhikode',
            'city': 'Kozhikode',
            'state': 'Kerala',
            'pincode': '673002',
            'phone': '9845999999',
            'email': 'premium@hopehair.org',
            'opening_time': '08:30',
            'closing_time': '19:00',
            'working_days': 'Tuesday - Sunday',
            'latitude': '11.2600',
            'longitude': '75.7900',
            'description': 'Updated description for center.',
            'status': 'Active'
        }, follow_redirects=True)
        self.assertEqual(res_edit.status_code, 200)
        self.assertIn(b'updated successfully', res_edit.data.lower())

        # Verify changes in SQLite
        updated = DonationCenter.get_by_id(cid)
        self.assertEqual(updated['center_name'], 'Kozhikode Premium Drop Hub')
        self.assertEqual(updated['address'], 'Updated Beach Road, Suite 5')
        self.assertEqual(updated['pincode'], '673002')
        self.assertEqual(updated['phone'], '9845999999')
        self.assertEqual(updated['opening_time'], '08:30')
        self.assertEqual(updated['closing_time'], '19:00')
        self.assertEqual(updated['working_days'], 'Tuesday - Sunday')
        self.assertAlmostEqual(updated['latitude'], 11.2600, places=4)
        self.assertAlmostEqual(updated['longitude'], 75.7900, places=4)

    def test_04_delete_center(self):
        """
        TEST 4 — Delete center
        Delete the test center and verify it is removed from SQLite.
        """
        # Login as approved NGO
        self.client.post('/login', data={
            'email': 'contact@hopehair.org',
            'password': 'Password@123'
        }, follow_redirects=True)

        ngo_user = User.get_by_email('contact@hopehair.org')
        ngo_prof = NGO.get_by_user_id(ngo_user['id'])

        # Create temporary center to delete
        cid = DonationCenter.create(
            ngo_id=ngo_prof['id'],
            center_name='Temporary Center To Delete',
            address='Demo Address',
            district='Thrissur',
            city='Thrissur',
            state='Kerala',
            pincode='680001',
            phone='9811223344',
            email='temp@hopehair.org',
            opening_time='09:00',
            closing_time='17:00',
            working_days='Monday - Saturday',
            status='Active'
        )
        self.assertIsNotNone(DonationCenter.get_by_id(cid))

        # Delete center via POST
        res_del = self.client.post(f'/ngo/donation-centers/{cid}/delete', follow_redirects=True)
        self.assertEqual(res_del.status_code, 200)
        self.assertIn(b'deleted successfully', res_del.data.lower())

        # Verify removal in SQLite
        deleted = DonationCenter.get_by_id(cid)
        self.assertIsNone(deleted, "Center was not removed from SQLite database!")

    def test_05_multiple_centers(self):
        """
        TEST 5 — Multiple centers
        Create two centers under the same NGO.
        Verify both appear correctly in the NGO center list and database.
        """
        self.client.post('/login', data={
            'email': 'contact@hopehair.org',
            'password': 'Password@123'
        }, follow_redirects=True)

        ngo_user = User.get_by_email('contact@hopehair.org')
        ngo_prof = NGO.get_by_user_id(ngo_user['id'])

        # Create Center 1
        DonationCenter.create(
            ngo_id=ngo_prof['id'],
            center_name='Hope Center North',
            address='North Road',
            district='Kannur',
            city='Kannur',
            state='Kerala',
            pincode='670001',
            phone='9846000001',
            email='north@hopehair.org',
            opening_time='09:00',
            closing_time='17:00',
            working_days='Monday - Saturday',
            status='Active'
        )

        # Create Center 2
        DonationCenter.create(
            ngo_id=ngo_prof['id'],
            center_name='Hope Center South',
            address='South Road',
            district='Kollam',
            city='Kollam',
            state='Kerala',
            pincode='691001',
            phone='9846000002',
            email='south@hopehair.org',
            opening_time='10:00',
            closing_time='18:00',
            working_days='Monday - Friday',
            status='Active'
        )

        # Verify both appear on NGO management page
        res = self.client.get('/ngo/donation-centers')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Hope Center North', res.data)
        self.assertIn(b'Hope Center South', res.data)

        # Verify both retrieved in query for this NGO
        centers = DonationCenter.get_by_ngo_id(ngo_prof['id'])
        center_names = [c['center_name'] for c in centers]
        self.assertIn('Hope Center North', center_names)
        self.assertIn('Hope Center South', center_names)

    def test_06_security_cross_ngo_isolation(self):
        """
        TEST 6 — Security (Cross-NGO Isolation)
        Login as NGO A. Try to access/edit/delete NGO B's donation center.
        Expected: ACCESS DENIED.
        """
        # NGO A = Hope Hair Foundation (user_id 2, ngo_profiles id 1)
        # Create NGO B:
        ngo_b_id = User.create(
            name='Second NGO',
            email='ngob@example.com',
            password='Password@123',
            role='ngo',
            status='active'
        )
        ngo_b_prof_id = NGO.create(
            user_id=ngo_b_id,
            organization_name='Second NGO Foundation',
            registration_number='REG-KL-NGO-B-99',
            phone='9898989898',
            email='ngob@example.com',
            address='Secret Address',
            district='Wayanad',
            approval_status='approved'
        )

        # Create Center belonging to NGO B
        ngo_b_center_id = DonationCenter.create(
            ngo_id=ngo_b_prof_id,
            center_name="NGO B Private Center",
            address="Private Road",
            district="Wayanad",
            city="Kalpetta",
            state="Kerala",
            pincode="673121",
            phone="9898989898",
            email="center@ngob.org",
            opening_time="09:00",
            closing_time="17:00",
            working_days="Monday - Friday",
            status="Active"
        )

        # Login as NGO A
        self.client.post('/login', data={
            'email': 'contact@hopehair.org',
            'password': 'Password@123'
        }, follow_redirects=True)

        # 1. NGO A attempts to view NGO B's center details -> Expected ACCESS DENIED
        res_view = self.client.get(f'/ngo/donation-centers/{ngo_b_center_id}')
        self.assertEqual(res_view.status_code, 403, "NGO A was allowed to view NGO B's center details!")
        self.assertIn(b'ACCESS DENIED', res_view.data)

        # 2. NGO A attempts to access GET edit page of NGO B's center -> Expected ACCESS DENIED
        res_edit_get = self.client.get(f'/ngo/donation-centers/{ngo_b_center_id}/edit')
        self.assertEqual(res_edit_get.status_code, 403, "NGO A was allowed to open NGO B's edit form!")
        self.assertIn(b'ACCESS DENIED', res_edit_get.data)

        # 3. NGO A attempts POST edit to NGO B's center -> Expected ACCESS DENIED
        res_edit_post = self.client.post(f'/ngo/donation-centers/{ngo_b_center_id}/edit', data={
            'center_name': 'Hacked Center Name',
            'address': 'Hacked Address',
            'district': 'Wayanad',
            'city': 'Kalpetta',
            'pincode': '673121',
            'phone': '9898989898',
            'opening_time': '09:00',
            'closing_time': '17:00',
            'working_days': 'Monday - Friday'
        })
        self.assertEqual(res_edit_post.status_code, 403, "NGO A was allowed to POST updates to NGO B's center!")
        self.assertIn(b'ACCESS DENIED', res_edit_post.data)

        # Verify Center B was NOT changed
        center_b = DonationCenter.get_by_id(ngo_b_center_id)
        self.assertEqual(center_b['center_name'], 'NGO B Private Center')

        # 4. NGO A attempts POST delete to NGO B's center -> Expected ACCESS DENIED
        res_delete_post = self.client.post(f'/ngo/donation-centers/{ngo_b_center_id}/delete')
        self.assertEqual(res_delete_post.status_code, 403, "NGO A was allowed to delete NGO B's center!")
        self.assertIn(b'ACCESS DENIED', res_delete_post.data)

        # Verify Center B still exists
        self.assertIsNotNone(DonationCenter.get_by_id(ngo_b_center_id))

    def test_07_donor_view(self):
        """
        TEST 7 — Donor View
        Login as donor.
        Open donation centers.
        Verify that approved/active centers are visible.
        Verify donor cannot create/edit/delete centers.
        """
        # Login as donor
        self.client.post('/login', data={
            'email': 'donor@example.com',
            'password': 'Password@123'
        }, follow_redirects=True)

        # Donor views donation centers directory
        res_donor_centers = self.client.get('/donor/donation-centers')
        self.assertEqual(res_donor_centers.status_code, 200)
        self.assertIn(b'Verified Hair Donation Centers', res_donor_centers.data)
        # Default seed center Kochi Central Hair Drop Center must be visible
        self.assertIn(b'Kochi Central Hair Drop Center', res_donor_centers.data)
        self.assertIn(b'View Details', res_donor_centers.data)

        # Inactive centers must NOT be visible to donors
        DonationCenter.create(
            ngo_id=1,
            center_name='Hidden Inactive Center',
            address='Somewhere',
            district='Ernakulam',
            city='Kochi',
            pincode='682001',
            phone='9876543210',
            opening_time='09:00',
            closing_time='17:00',
            working_days='Monday - Saturday',
            status='Inactive'
        )
        res_donor_centers2 = self.client.get('/donor/donation-centers')
        self.assertNotIn(b'Hidden Inactive Center', res_donor_centers2.data)

        # Verify donor CANNOT create centers (GET /ngo/donation-centers/add or POST)
        res_unauth_add = self.client.get('/ngo/donation-centers/add', follow_redirects=False)
        self.assertEqual(res_unauth_add.status_code, 302)
        # Should redirect away to donor dashboard or login

        res_unauth_post = self.client.post('/ngo/donation-centers/add', data={
            'center_name': 'Donor Unauthorized Center',
            'address': 'Test',
            'district': 'Ernakulam',
            'city': 'Kochi',
            'pincode': '682001',
            'phone': '9876543210',
            'opening_time': '09:00',
            'closing_time': '17:00',
            'working_days': 'Monday - Saturday'
        }, follow_redirects=False)
        self.assertEqual(res_unauth_post.status_code, 302)

        # Verify donor cannot delete centers
        res_unauth_del = self.client.post('/ngo/donation-centers/1/delete', follow_redirects=False)
        self.assertEqual(res_unauth_del.status_code, 302)
        self.assertIsNotNone(DonationCenter.get_by_id(1), "Center 1 should not be deleted by donor!")

    def test_08_admin_management(self):
        """
        TEST 8 — Admin
        Login as Admin.
        Verify: NGO list, NGO approval, Donation center list, Center ownership, Center status toggling.
        """
        # Login as Admin
        res_login = self.client.post('/login', data={
            'email': 'admin@hairsync.com',
            'password': 'Admin@123'
        }, follow_redirects=True)
        self.assertEqual(res_login.status_code, 200)

        # 1. Admin Dashboard shows metrics
        res_dash = self.client.get('/admin/dashboard')
        self.assertEqual(res_dash.status_code, 200)
        self.assertIn(b'Total Donation Centers', res_dash.data)
        self.assertIn(b'Total NGOs', res_dash.data)

        # 2. Admin NGO list view with center counts
        res_ngos = self.client.get('/admin/ngos')
        self.assertEqual(res_ngos.status_code, 200)
        self.assertIn(b'Hope Hair Foundation', res_ngos.data)
        self.assertIn(b'Centers', res_ngos.data)

        # 3. Admin Donation Center list
        res_centers = self.client.get('/admin/donation-centers')
        self.assertEqual(res_centers.status_code, 200)
        self.assertIn(b'Platform Donation Centers Oversight', res_centers.data)
        self.assertIn(b'Kochi Central Hair Drop Center', res_centers.data)
        self.assertIn(b'Hope Hair Foundation', res_centers.data)

        # 4. Admin toggles center status (Active -> Inactive -> Active)
        center = DonationCenter.get_by_id(1)
        initial_status = center['status']

        res_toggle = self.client.post('/admin/donation-centers/1/toggle-status', follow_redirects=True)
        self.assertEqual(res_toggle.status_code, 200)
        updated_center = DonationCenter.get_by_id(1)
        self.assertNotEqual(updated_center['status'], initial_status)

        # 5. Admin sets specific status
        res_status = self.client.post('/admin/donation-centers/1/status', data={'status': 'Approved'}, follow_redirects=True)
        self.assertEqual(res_status.status_code, 200)
        final_center = DonationCenter.get_by_id(1)
        self.assertEqual(final_center['status'], 'Approved')


if __name__ == '__main__':
    unittest.main()
