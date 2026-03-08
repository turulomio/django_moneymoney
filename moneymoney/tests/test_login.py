from django.conf import settings
from django.contrib.auth.models import User
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token
from moneymoney.reusing import tests_helpers

TEST_USERNAME = "testuser"
TEST_PASSWORD = "testuser_password"
TEST_E2E_USERNAME = "test"
TEST_E2E_PASSWORD = "test"

def _create_test_user():
    user=User.objects.create(username=TEST_USERNAME)
    user.set_password(TEST_PASSWORD)
    user.save()
    return user

def _create_test_e2e_user():
    user=User.objects.create(username=TEST_E2E_USERNAME)
    user.set_password(TEST_E2E_PASSWORD)
    user.save()
    return user

def test_successful_login_and_logout(self):
    """
    Test that a user can successfully log in with valid credentials.
    """
    test_user=_create_test_user()
    payload = {
        "username": TEST_USERNAME,
        "password": TEST_PASSWORD
    }
    response_key = tests_helpers.client_post(self, self.client_anonymous, "/login/", payload, status.HTTP_200_OK)
    self.assertIsInstance(response_key, str) # Expecting the token key as a string
    self.assertTrue(Token.objects.filter(key=response_key, user=test_user).exists())

    # Then, log out using the token
    logout_payload = {"key": response_key}
    response = tests_helpers.client_post(self, self.client_anonymous, "/logout/", logout_payload, status.HTTP_200_OK)
    self.assertEqual(response, "Logged out")
    self.assertFalse(Token.objects.filter(key=response_key, user=test_user).exists())

def test_failed_login_invalid_username(self):
    """
    Test that login fails with an invalid username.
    """
    test_user=_create_test_user()
    payload = {
        "username": "bad_username",
        "password": TEST_PASSWORD
    }
    response = tests_helpers.client_post(self, self.client_anonymous, "/login/", payload, status.HTTP_401_UNAUTHORIZED)
    self.assertEqual(response, "Wrong credentials")

def test_failed_login_invalid_password(self):
    """
    Test that login fails with an invalid password for an existing user.
    """
    test_user=_create_test_user()
    payload = {
        "username": TEST_USERNAME,
        "password": "bad_password"
    }
    response = tests_helpers.client_post(self, self.client_anonymous, "/login/", payload, status.HTTP_401_UNAUTHORIZED)
    self.assertEqual(response, "Wrong credentials")

def test_failed_login_missing_credentials(self):
    """
    Test that login fails if username or password is missing.
    """
    test_user=_create_test_user()

    # Missing username
    payload_no_username = {
        "password": TEST_PASSWORD,
    }
    response = tests_helpers.client_post(self, self.client_anonymous, "/login/", payload_no_username, status.HTTP_401_UNAUTHORIZED)
    self.assertEqual(response, "Wrong credentials")

    # Missing password
    payload_no_password = {
        "username": TEST_USERNAME,
    }
    response = tests_helpers.client_post(self, self.client_anonymous, "/login/", payload_no_password, status.HTTP_401_UNAUTHORIZED)
    self.assertEqual(response, "Wrong credentials")


def test_failed_logout_invalid_token(self):
    """
    Test that logout fails with an invalid or non-existent token.
    """
    logout_payload = {"key": "invalid_token_123"}
    response = tests_helpers.client_post(self, self.client_anonymous, "/logout/", logout_payload, status.HTTP_403_FORBIDDEN)
    self.assertEqual(response, "Invalid token")

def test_failed_logout_missing_token(self):
    """
    Test that logout fails if the token key is missing from the payload.
    """
    logout_payload = {}
    response = tests_helpers.client_post(self, self.client_anonymous, "/logout/", logout_payload, status.HTTP_403_FORBIDDEN)
    self.assertEqual(response, "Invalid token")

@override_settings(E2E_TESTING=True)
def test_login_token_management_e2e_true(self):
    """
    Test token management when E2E_TESTING is True: existing token is updated to "testing_e2e_token".
    """
    test_user=_create_test_e2e_user() #No existe por defecto solo cuando se ejecuta poe testserver_e2e

    payload = {"username": TEST_E2E_USERNAME, "password": TEST_E2E_PASSWORD}
    response_key = tests_helpers.client_post(self, self.client_anonymous, "/login/", payload, status.HTTP_200_OK)
    self.assertEqual(response_key, "testing_e2e_token")
    self.assertEqual(Token.objects.get(user=test_user).key, "testing_e2e_token")
    self.assertEqual(Token.objects.filter(user=test_user).count(), 1)

    # Logins again and continue to be the same and only on token
    response_key = tests_helpers.client_post(self, self.client_anonymous, "/login/", payload, status.HTTP_200_OK)
    self.assertEqual(response_key, "testing_e2e_token")
    self.assertEqual(Token.objects.get(user=test_user).key, "testing_e2e_token")
    self.assertEqual(Token.objects.filter(user=test_user).count(), 1)

@override_settings(E2E_TESTING=False)
def test_login_token_management_e2e_false(self):
    """
    Test token management when E2E_TESTING is False: existing token is deleted and a new one is created.
    """
    test_user=_create_test_e2e_user() #No existe por defecto solo cuando se ejecuta poe testserver_e2e

    payload = {"username": TEST_E2E_USERNAME, "password": TEST_E2E_PASSWORD}
    response_key = tests_helpers.client_post(self, self.client_anonymous, "/login/", payload, status.HTTP_200_OK)
    self.assertNotEqual(response_key, "testing_e2e_token")
    self.assertNotEqual(Token.objects.get(user=test_user).key, "testing_e2e_token")
    self.assertEqual(Token.objects.filter(user=test_user).count(), 1)

def test_access_protected_resource_after_login(self):
    """
    Test that a user can access a protected resource after successful login.
    """
    test_user=_create_test_user()    # 1. Log in to get a token
    login_payload = {"username": TEST_USERNAME, "password": TEST_PASSWORD}
    token_key = tests_helpers.client_post(self, self.client_anonymous, "/login/", login_payload, status.HTTP_200_OK)

    # 2. Create a new APIClient instance and set credentials
    authenticated_client = APIClient()
    authenticated_client.credentials(HTTP_AUTHORIZATION=f'Token {token_key}')
    authenticated_client.user=test_user #For compatibility of my tests

    # 3. Try to access a protected resource (e.g., user profile)
    # Assuming /profile/ is a protected endpoint that requires authentication (from moneymoney/views.py)
    response = tests_helpers.client_get(self, authenticated_client, "/profile/", status.HTTP_200_OK)
    self.assertIn("email", response) # Check for a known field in the profile response

def test_access_protected_resource_after_logout(self):
    """
    Test that a user cannot access a protected resource after successful logout.
    """
    test_user=_create_test_user()    # 1. Log in to get a token
    login_payload = {"username": TEST_USERNAME, "password": TEST_PASSWORD}
    token_key = tests_helpers.client_post(self, self.client_anonymous, "/login/", login_payload, status.HTTP_200_OK)

    # 2. Create a new APIClient instance and set credentials
    authenticated_client = APIClient()
    authenticated_client.credentials(HTTP_AUTHORIZATION=f'Token {token_key}')
    authenticated_client.user=test_user #For compatibility of my tests

    logout_payload = {"key": token_key}
    response = tests_helpers.client_post(self, authenticated_client, "/logout/", logout_payload, status.HTTP_200_OK)

    # 3. Try to access a protected resource (e.g., user profile)
    # Assuming /profile/ is a protected endpoint that requires authentication (from moneymoney/views.py)
    response = tests_helpers.client_get(self, authenticated_client, "/profile/", status.HTTP_401_UNAUTHORIZED)
