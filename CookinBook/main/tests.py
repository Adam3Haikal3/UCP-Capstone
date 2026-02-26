from django.test import TestCase

# Create your tests here.
class SimplePagesTest(TestCase):
    def test_home_page_returns_200(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

    def test_login_page_returns_200(self):
        response = self.client.get("/login/")
        self.assertEqual(response.status_code, 200)

    def test_signup_page_returns_200(self):
        response = self.client.get("/signup/")
        self.assertEqual(response.status_code, 200)