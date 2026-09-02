"""
HairSync Module 1 Test Suite
Tests:
1. Public route availability
2. Authentication protection & redirect checks
3. Mock session role tests & authorization restrictions
4. Template rendering checks
"""

import unittest
from app import create_app


class Module1TestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_public_pages(self):
        pages = ['/', '/login', '/register', '/register?role=donor', '/register?role=ngo', '/register?role=recipient']
        for page in pages:
            with self.subTest(page=page):
                res = self.client.get(page)
                self.assertEqual(res.status_code, 200, f"Page {page} failed to load.")

    def test_404_page(self):
        res = self.client.get('/nonexistent-test-page')
        self.assertEqual(res.status_code, 404)
        self.assertIn(b'Page Not Found', res.data)


    def test_unauthenticated_protected_routes(self):
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
                self.assertEqual(res.status_code, 302, f"Route {route} did not redirect.")
                self.assertIn('/login', res.headers.get('Location', ''))

    def test_role_authorization_isolation(self):
        # A Donor should NOT be allowed to access /admin/dashboard
        with self.client.session_transaction() as sess:
            sess['user_id'] = 4
            sess['user_name'] = 'Test Donor'
            sess['user_email'] = 'donor@test.com'
            sess['role'] = 'donor'

        res = self.client.get('/admin/dashboard', follow_redirects=False)
        self.assertEqual(res.status_code, 302, "Donor was able to access Admin dashboard!")
        # Should redirect to donor dashboard
        self.assertIn('/donor/dashboard', res.headers.get('Location', ''))

        # A Recipient should NOT be allowed to access /ngo/dashboard
        with self.client.session_transaction() as sess:
            sess['user_id'] = 5
            sess['user_name'] = 'Test Recipient'
            sess['user_email'] = 'recipient@test.com'
            sess['role'] = 'recipient'

        res = self.client.get('/ngo/dashboard', follow_redirects=False)
        self.assertEqual(res.status_code, 302, "Recipient was able to access NGO dashboard!")
        self.assertIn('/recipient/dashboard', res.headers.get('Location', ''))

    def test_logout(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['role'] = 'admin'

        res = self.client.get('/logout', follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertIn('/login', res.headers.get('Location', ''))

        # Verify session cleared
        with self.client.session_transaction() as sess:
            self.assertNotIn('user_id', sess)


if __name__ == '__main__':
    unittest.main()
