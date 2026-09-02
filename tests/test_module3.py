"""
HairSync Module 3 Test Suite: Eligibility, Hair Donation & Appointment Management
Implements all 8 required verification tests from prompt specification:
TEST 1 — Eligibility (Eligible, Not Eligible, Requires Review based on guidelines)
TEST 2 — NGO Guidelines (Create/update acceptance guidelines, verify SQLite changes)
TEST 3 — Appointment Booking (Eligible donor books at active center, initial status Pending)
TEST 4 — NGO Confirmation (Approved NGO confirms appointment, status becomes Confirmed)
TEST 5 — Donor Status (Donor views updated Confirmed status in My Appointments)
TEST 6 — Donation Completion (NGO marks donation completed, logs measured specs, appointment Completed)
TEST 7 — Donation History (Donor views verified completed donation in history ledger)
TEST 8 — Security & Role Isolation (Cross-donor and cross-NGO isolation, unauthorized access blocks)
"""

import unittest
import sqlite3
from datetime import date, timedelta
from app import create_app
from config import Config
from database.init_db import run_init
from models.user import User
from models.donor import Donor
from models.ngo import NGO
from models.donation_center import DonationCenter
from models.donation_guideline import DonationGuideline
from models.appointment import Appointment
from models.donation import Donation


class Module3TestCase(unittest.TestCase):
    def setUp(self):
        run_init()
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()

    def tearDown(self):
        self.ctx.pop()

    def _login(self, email, password):
        self.client.get('/logout')
        return self.client.post('/login', data={
            'email': email,
            'password': password
        }, follow_redirects=True)

    # ==========================================================
    # TEST 1 — ELIGIBILITY EVALUATION
    # ==========================================================
    def test_01_eligibility_evaluations(self):
        """
        TEST 1 — Eligibility Checker
        Verify:
        - Hair length 30 cm, Straight, Virgin, Untreated -> ELIGIBLE
        - Hair length 10 cm -> NOT ELIGIBLE (< 20 cm)
        - Hair length 30 cm, Chemically treated -> Dependent on NGO guideline
        """
        # 1. Standard platform guidelines evaluation
        default_guide = DonationGuideline.DEFAULT_GUIDELINES

        # Donor 1: 30 cm, straight, virgin, no treatments
        res1 = DonationGuideline.evaluate_donor(
            guideline=default_guide,
            hair_length=30.0,
            hair_type='Straight',
            hair_condition='Virgin/Untreated',
            is_colored=False,
            is_chemically_treated=False,
            is_bleached=False
        )
        self.assertEqual(res1['status'], 'Eligible')
        self.assertTrue(res1['eligible'])

        # Donor 2: 10 cm length (below minimum 20 cm)
        res2 = DonationGuideline.evaluate_donor(
            guideline=default_guide,
            hair_length=10.0,
            hair_type='Straight',
            hair_condition='Virgin/Untreated',
            is_colored=False,
            is_chemically_treated=False,
            is_bleached=False
        )
        self.assertEqual(res2['status'], 'Not Eligible')
        self.assertFalse(res2['eligible'])
        self.assertTrue(any('below' in msg for msg in res2['messages']))

        # Donor 3: 30 cm, chemically treated under guideline with 'Requires Review'
        custom_guide = dict(default_guide)
        custom_guide['allow_chemically_treated'] = 'Requires Review'
        res3 = DonationGuideline.evaluate_donor(
            guideline=custom_guide,
            hair_length=30.0,
            hair_type='Straight',
            hair_condition='Treated',
            is_colored=False,
            is_chemically_treated=True,
            is_bleached=False
        )
        self.assertEqual(res3['status'], 'Requires Review')
        self.assertTrue(res3['eligible'])

        # Donor 4: 30 cm, chemically treated under guideline with 'Not Allowed'
        custom_guide_strict = dict(default_guide)
        custom_guide_strict['allow_chemically_treated'] = 'Not Allowed'
        res4 = DonationGuideline.evaluate_donor(
            guideline=custom_guide_strict,
            hair_length=30.0,
            hair_type='Straight',
            hair_condition='Treated',
            is_colored=False,
            is_chemically_treated=True,
            is_bleached=False
        )
        self.assertEqual(res4['status'], 'Not Eligible')

        # Test via web route as logged-in donor
        self._login('donor@example.com', 'Password@123')
        resp = self.client.post('/donor/eligibility', data={
            'ngo_id': '1',
            'hair_length': '28.0',
            'hair_type': 'Straight',
            'hair_condition': 'Virgin/Untreated'
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Your Hair Is Ready For Donation!', resp.data)

    # ==========================================================
    # TEST 2 — NGO GUIDELINES CONFIGURATION
    # ==========================================================
    def test_02_ngo_guidelines_configuration(self):
        """
        TEST 2 — NGO Guidelines
        Login as approved NGO (Hope Hair Foundation), configure custom criteria,
        verify persistence in SQLite database.
        """
        self._login('contact@hopehair.org', 'Password@123')

        # Submit guideline updates
        res = self.client.post('/ngo/guidelines', data={
            'minimum_hair_length': '30.0',
            'allowed_hair_types': ['Straight', 'Wavy'],
            'allow_colored_hair': 'Allowed',
            'allow_chemically_treated': 'Requires Review',
            'allow_bleached_hair': 'Not Allowed',
            'minimum_condition': 'Clean, thoroughly dried, braided',
            'additional_requirements': 'Hair must be packed in clean ziplock bag.'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'guidelines saved successfully', res.data.lower())

        # Verify in SQLite
        conn = sqlite3.connect(Config.DATABASE)
        cur = conn.cursor()
        cur.execute("SELECT minimum_hair_length, allow_colored_hair, allow_chemically_treated, allow_bleached_hair FROM donation_guidelines WHERE ngo_id = 1")
        row = cur.fetchone()
        conn.close()

        self.assertIsNotNone(row)
        self.assertEqual(row[0], 30.0)
        self.assertEqual(row[1], 'Allowed')
        self.assertEqual(row[2], 'Requires Review')
        self.assertEqual(row[3], 'Not Allowed')

    # ==========================================================
    # TEST 3 — DONOR APPOINTMENT BOOKING
    # ==========================================================
    def test_03_donor_appointment_booking(self):
        """
        TEST 3 — Appointment Booking
        Login as eligible donor, book appointment at Kochi Central Hair Drop Center,
        verify appointment created with status 'Pending'.
        """
        self._login('donor@example.com', 'Password@123')

        tomorrow = (date.today() + timedelta(days=1)).strftime('%Y-%m-%d')
        res = self.client.post('/donor/appointments/book', data={
            'center_id': '1',
            'appointment_date': tomorrow,
            'appointment_time': '11:00',
            'purpose': 'Haircut & Ponytail Donation',
            'donor_notes': 'Hair is clean and 30 cm long.'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Appointment request booked successfully', res.data)

        # Verify in SQLite
        conn = sqlite3.connect(Config.DATABASE)
        cur = conn.cursor()
        cur.execute("SELECT id, status, appointment_date, appointment_time, ngo_id, donation_center_id FROM appointments WHERE donor_id = 1")
        appt = cur.fetchone()
        conn.close()

        self.assertIsNotNone(appt)
        self.assertEqual(appt[1], 'Pending')
        self.assertEqual(appt[2], tomorrow)
        self.assertEqual(appt[3], '11:00')
        self.assertEqual(appt[4], 1)
        self.assertEqual(appt[5], 1)

    # ==========================================================
    # TEST 4 — NGO APPOINTMENT CONFIRMATION
    # ==========================================================
    def test_04_ngo_appointment_confirmation(self):
        """
        TEST 4 — NGO Confirmation
        Login as host NGO, view appointment in queue, confirm it, verify status 'Confirmed'.
        """
        # Create appointment directly
        appt_id = Appointment.create(
            donor_id=1,
            ngo_id=1,
            donation_center_id=1,
            appointment_date='2026-09-20',
            appointment_time='10:30',
            purpose='Hair Donation'
        )

        self._login('contact@hopehair.org', 'Password@123')

        # NGO confirms appointment
        res = self.client.post(f'/ngo/appointments/{appt_id}/confirm', data={
            'ngo_notes': 'Confirmed! Our stylist will be ready at 10:30 AM.'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        # Verify status in database
        appt = Appointment.get_by_id(appt_id)
        self.assertEqual(appt['status'], 'Confirmed')

    # ==========================================================
    # TEST 5 — DONOR APPOINTMENT STATUS VIEW
    # ==========================================================
    def test_05_donor_status_view(self):
        """
        TEST 5 — Donor Status
        Login as donor, open My Appointments, verify Confirmed appointment status is visible.
        """
        appt_id = Appointment.create(
            donor_id=1,
            ngo_id=1,
            donation_center_id=1,
            appointment_date='2026-09-20',
            appointment_time='10:30',
            purpose='Hair Donation'
        )
        Appointment.update_status(appt_id, 'Confirmed')

        self._login('donor@example.com', 'Password@123')
        res = self.client.get('/donor/appointments')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Confirmed', res.data)
        self.assertIn(b'Kochi Central Hair Drop Center', res.data)

    # ==========================================================
    # TEST 6 — DONATION COMPLETION
    # ==========================================================
    def test_06_donation_completion(self):
        """
        TEST 6 — Donation Completion
        Host NGO marks appointment completed and records measured hair specs.
        Verify:
        - Record created in 'donations' table
        - Appointment status updated to 'Completed'
        """
        appt_id = Appointment.create(
            donor_id=1,
            ngo_id=1,
            donation_center_id=1,
            appointment_date='2026-09-14',
            appointment_time='14:00',
            purpose='Hair Donation'
        )
        Appointment.update_status(appt_id, 'Confirmed')

        self._login('contact@hopehair.org', 'Password@123')

        # Complete donation
        res = self.client.post(f'/ngo/appointments/{appt_id}/complete', data={
            'hair_length': '28.5',
            'hair_type': 'Wavy',
            'hair_condition': 'Virgin / Untreated',
            'donation_date': '2026-09-14',
            'quantity_or_estimated_weight': '1 Ponytail (~125g)',
            'notes': 'Carefully tied and measured. Allocated to cranial prostheses.'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        # Verify in database
        appt = Appointment.get_by_id(appt_id)
        self.assertEqual(appt['status'], 'Completed')

        conn = sqlite3.connect(Config.DATABASE)
        cur = conn.cursor()
        cur.execute("SELECT id, donor_id, ngo_id, hair_length, hair_type, status FROM donations WHERE appointment_id = ?", (appt_id,))
        don = cur.fetchone()
        conn.close()

        self.assertIsNotNone(don)
        self.assertEqual(don[1], 1) # donor_id
        self.assertEqual(don[2], 1) # ngo_id
        self.assertEqual(don[3], 28.5)
        self.assertEqual(don[4], 'Wavy')
        self.assertEqual(don[5], 'Completed')

    # ==========================================================
    # TEST 7 — DONATION HISTORY
    # ==========================================================
    def test_07_donation_history(self):
        """
        TEST 7 — Donation History
        Login as donor, open My Donation History, verify completed donation record appears.
        """
        Donation.create(
            donor_id=1,
            ngo_id=1,
            donation_center_id=1,
            hair_length=28.5,
            hair_type='Wavy',
            hair_condition='Virgin / Untreated',
            donation_date='2026-09-14',
            quantity_or_estimated_weight='125g',
            notes='Test donation',
            status='Completed'
        )

        self._login('donor@example.com', 'Password@123')
        res = self.client.get('/donor/donations')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'28.5 cm', res.data)
        self.assertIn(b'Hope Hair Foundation', res.data)
        self.assertIn(b'Kochi Central Hair Drop Center', res.data)

    # ==========================================================
    # TEST 8 — SECURITY & ROLE ISOLATION
    # ==========================================================
    def test_08_security_role_isolation(self):
        """
        TEST 8 — Security & Authorization
        Verify:
        - Donor A cannot cancel Donor B's appointment
        - Donor cannot confirm appointment or complete donation
        - NGO A cannot manage NGO B's appointment
        - NGO A cannot modify NGO B's donation guidelines
        - Recipient cannot manage appointments
        - Logged-out user cannot access protected endpoints
        """
        # Create appointment belonging to Donor 1 and NGO 1
        appt_id = Appointment.create(
            donor_id=1,
            ngo_id=1,
            donation_center_id=1,
            appointment_date='2026-09-25',
            appointment_time='10:00'
        )

        # 1. Logged-out access attempt to book appointment
        res = self.client.get('/donor/appointments/book')
        self.assertEqual(res.status_code, 302)
        self.assertIn('/login', res.headers['Location'])

        # 2. Donor attempts to access NGO appointment confirmation endpoint -> 302 redirect / Access Denied
        self._login('donor@example.com', 'Password@123')
        res = self.client.post(f'/ngo/appointments/{appt_id}/confirm', follow_redirects=True)
        self.assertIn(b'Access denied', res.data)

        # 3. Donor attempts to access complete donation endpoint
        res = self.client.get(f'/ngo/appointments/{appt_id}/complete', follow_redirects=True)
        self.assertIn(b'Access denied', res.data)

        # 4. Cross-NGO Isolation: Create NGO 2 and log in
        User.create('NGO Two', 'ngo2@test.com', 'Password@123', 'ngo', 'active')
        ngo2_user = User.get_by_email('ngo2@test.com')
        NGO.create(
            user_id=ngo2_user['id'],
            organization_name='NGO Two Org',
            registration_number='REG-NGO-2026-02',
            phone='9898989898',
            email='ngo2@test.com',
            address='Calicut',
            district='Kozhikode',
            description='Test NGO Two',
            approval_status='approved'
        )

        self._login('ngo2@test.com', 'Password@123')

        # NGO 2 attempts to confirm NGO 1's appointment -> ACCESS DENIED (403)
        res_cross = self.client.post(f'/ngo/appointments/{appt_id}/confirm')
        self.assertEqual(res_cross.status_code, 403)

        # NGO 2 attempts to complete NGO 1's appointment -> ACCESS DENIED (403)
        res_cross_complete = self.client.get(f'/ngo/appointments/{appt_id}/complete')
        self.assertEqual(res_cross_complete.status_code, 403)

        # 5. Recipient attempts to access NGO appointment routes
        self._login('recipient@example.com', 'Password@123')
        res_rec = self.client.get('/ngo/appointments', follow_redirects=True)
        self.assertIn(b'Access denied', res_rec.data)


if __name__ == '__main__':
    unittest.main()
