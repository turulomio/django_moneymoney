from django.conf import settings
from django.contrib.auth.models import User
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token
from moneymoney.reusing import tests_helpers

TEST_USERNAME = "test_user"
TEST_PASSWORD = "testpassword123"

def _create_test_user():
    user=User.objects.create(username=TEST_USERNAME)
    user.set_password(TEST_PASSWORD)
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

# def test_failed_login_invalid_username(self):
#     """
#     Test that login fails with an invalid username.
#     """
#     test_password = "testpassword123"
#     payload = {
#         "username": "nonexistentuser",
#         "password": test_password,
#     }
#     response = tests_helpers.client_post(self, self.client_anonymous, "/login/", payload, status.HTTP_401_UNAUTHORIZED)
#     self.assertEqual(response, "Wrong credentials")

# def test_failed_login_invalid_password(self):
#     """
#     Test that login fails with an invalid password for an existing user.
#     """
#     test_username = self.user_authorized_1.username
#     payload = {
#         "username": test_username,
#         "password": "wrongpassword",
#     }
#     response = tests_helpers.client_post(self, self.client_anonymous, "/login/", payload, status.HTTP_401_UNAUTHORIZED)
#     self.assertEqual(response, "Wrong credentials")

# def test_failed_login_missing_credentials(self):
#     """
#     Test that login fails if username or password is missing.
#     """
#     test_username = self.user_authorized_1.username
#     test_password = "testpassword123"

#     # Missing username
#     payload_no_username = {
#         "password": test_password,
#     }
#     response = tests_helpers.client_post(self, self.client_anonymous, "/login/", payload_no_username, status.HTTP_401_UNAUTHORIZED)
#     self.assertEqual(response, "Wrong credentials")

#     # Missing password
#     payload_no_password = {
#         "username": test_username,
#     }
#     response = tests_helpers.client_post(self, self.client_anonymous, "/login/", payload_no_password, status.HTTP_401_UNAUTHORIZED)
#     self.assertEqual(response, "Wrong credentials")


# def test_failed_logout_invalid_token(self):
#     """
#     Test that logout fails with an invalid or non-existent token.
#     """
#     logout_payload = {"key": "invalid_token_123"}
#     response = tests_helpers.client_post(self, self.client_anonymous, "/logout/", logout_payload, status.HTTP_403_FORBIDDEN)
#     self.assertEqual(response, "Invalid token")

# def test_failed_logout_missing_token(self):
#     """
#     Test that logout fails if the token key is missing from the payload.
#     """
#     logout_payload = {}
#     response = tests_helpers.client_post(self, self.client_anonymous, "/logout/", logout_payload, status.HTTP_403_FORBIDDEN)
#     self.assertEqual(response, "Invalid token")

# @override_settings(E2E_TESTING=True)
# def test_login_token_management_e2e_true(self):
#     """
#     Test token management when E2E_TESTING is True: existing token is updated to "testing_e2e_token".
#     """
#     # Ensure no token exists initially for this user, or delete it if it does
#     Token.objects.filter(user=self.user_authorized_1).delete()
    
#     # Create an initial token for the user (this will be updated)
#     # Note: self.user_authorized_1 is available from MoneyMoneyAPITestCase
#     initial_token = Token.objects.create(user=self.user_authorized_1, key="old_token_key")
#     self.assertEqual(Token.objects.get(user=self.user_authorized_1).key, "old_token_key")

#     payload = {"username": test_username, "password": test_password}
#     response_key = tests_helpers.client_post(self, self.client_anonymous, "/login/", payload, status.HTTP_200_OK)
    
#     self.assertEqual(response_key, "testing_e2e_token")
#     self.assertEqual(Token.objects.get(user=self.user_authorized_1).key, "testing_e2e_token")
#     # Ensure no new token was created, but the existing one was updated
#     self.assertEqual(Token.objects.filter(user=self.user_authorized_1).count(), 1)

# @override_settings(E2E_TESTING=False)
# def test_login_token_management_e2e_false(self):
#     """
#     Test token management when E2E_TESTING is False: existing token is deleted and a new one is created.
#     """
#     # Ensure no token exists initially for this user, or delete it if it does
#     Token.objects.filter(user=self.user_authorized_1).delete()

#     # Create an initial token for the user
#     # Note: self.user_authorized_1 is available from MoneyMoneyAPITestCase
#     initial_token = Token.objects.create(user=self.user_authorized_1, key="old_token_key")
#     self.assertEqual(Token.objects.get(user=self.user_authorized_1).key, "old_token_key")

#     payload = {"username": test_username, "password": test_password}
#     response_key = tests_helpers.client_post(self, self.client_anonymous, "/login/", payload, status.HTTP_200_OK)
    
#     # A new token should have been generated, so its key should be different from the old one
#     self.assertNotEqual(response_key, "old_token_key")
#     self.assertTrue(Token.objects.filter(key=response_key, user=self.user_authorized_1).exists())
#     # Ensure the old token is gone and only one new token exists
#     self.assertFalse(Token.objects.filter(key="old_token_key").exists())
#     self.assertEqual(Token.objects.filter(user=self.user_authorized_1).count(), 1)

# def test_access_protected_resource_after_login(self):
#     """
#     Test that a user can access a protected resource after successful login.
#     """
#     test_username = self.user_authorized_1.username
#     test_password = "testpassword123"

#     # 1. Log in to get a token
#     login_payload = {"username": test_username, "password": test_password}
#     token_key = tests_helpers.client_post(self, self.client_anonymous, "/login/", login_payload, status.HTTP_200_OK)

#     # 2. Create a new APIClient instance and set credentials
#     authenticated_client = APIClient()
#     authenticated_client.credentials(HTTP_AUTHORIZATION=f'Token {token_key}')

#     # 3. Try to access a protected resource (e.g., user profile)
#     # Assuming /profile/ is a protected endpoint that requires authentication (from moneymoney/views.py)
#     response = tests_helpers.client_get(self, authenticated_client, "/profile/", status.HTTP_200_OK)
#     self.assertIn("email", response) # Check for a known field in the profile response
#     self.assertEqual(response["email"], self.user_authorized_1.email)

# def test_access_protected_resource_after_logout(self):
#     """
#     Test that a user cannot access a protected resource after successful logout.
#     """
#     test_username = self.user_authorized_1.username
#     test_password = "testpassword123"

#     # 1. Log in to get a token
#     login_payload = {"username": test_username, "password": test_password}
#     token_key = tests_helpers.client_post(self, self.client_anonymous, "/login/", login_payload, status.HTTP_200_OK)

#     # 2. Create a new APIClient instance and set credentials
#     authenticated_client = APIClient()
#     authenticated_client.credentials(HTTP_AUTHORIZATION=f'Token {token_key}')

#     # 3. Log out using the token (using the anonymous client to send the payload)
#     logout_payload = {"key": token_key}
#     tests_helpers.client_post(self, self.client_anonymous, "/logout/", logout_payload, status.HTTP_200_OK)
#     self.assertFalse(Token.objects.filter(key=token_key).exists())

#     # 4. Try to access the protected resource with the now invalidated token using the authenticated client
#     response = tests_helpers.client_get(self, authenticated_client, "/profile/", status.HTTP_401_UNAUTHORIZED)
#     self.assertEqual(response, {'detail': 'Invalid token.'})

# @override_settings(E2E_TESTING=False)
# def test_login_with_existing_token_e2e_false_multiple_times(self):
#     """
#     Test that logging in multiple times when E2E_TESTING is False
#     always results in a new token and invalidates previous ones.
#     """
#     test_username = self.user_authorized_1.username
#     test_password = "testpassword123"

#     # Ensure no token exists initially for this user, or delete it if it does
#     Token.objects.filter(user=self.user_authorized_1).delete()

#     # First login
#     payload = {"username": test_username, "password": test_password}
#     token_key_1 = tests_helpers.client_post(self, self.client_anonymous, "/login/", payload, status.HTTP_200_OK)
#     self.assertTrue(Token.objects.filter(key=token_key_1, user=self.user_authorized_1).exists())
#     self.assertEqual(Token.objects.filter(user=self.user_authorized_1).count(), 1)

#     # Second login
#     token_key_2 = tests_helpers.client_post(self, self.client_anonymous, "/login/", payload, status.HTTP_200_OK)
#     self.assertTrue(Token.objects.filter(key=token_key_2, user=self.user_authorized_1).exists())
#     self.assertEqual(Token.objects.filter(user=self.user_authorized_1).count(), 1) # Still only one token
#     self.assertNotEqual(token_key_1, token_key_2) # New token should be different
#     self.assertFalse(Token.objects.filter(key=token_key_1).exists()) # Old token should be deleted

#     # Try to use the first token (should fail)
#     client_with_old_token = APIClient()
#     client_with_old_token.credentials(HTTP_AUTHORIZATION=f'Token {token_key_1}')
#     tests_helpers.client_get(self, client_with_old_token, "/profile/", status.HTTP_401_UNAUTHORIZED)

#     # Try to use the second token (should succeed)
#     client_with_new_token = APIClient()
#     client_with_new_token.credentials(HTTP_AUTHORIZATION=f'Token {token_key_2}')
#     tests_helpers.client_get(self, client_with_new_token, "/profile/", status.HTTP_200_OK)

# @override_settings(E2E_TESTING=True)
# def test_login_with_existing_token_e2e_true_multiple_times(self):
#     """
#     Test that logging in multiple times when E2E_TESTING is True
#     always results in the same "testing_e2e_token".
#     """    
#     test_username = self.user_authorized_1.username
#     test_password = "testpassword123"

#     # Ensure no token exists initially for this user, or delete it if it does
#     Token.objects.filter(user=self.user_authorized_1).delete()

#     # First login
#     payload = {"username": test_username, "password": test_password}
#     token_key_1 = tests_helpers.client_post(self, self.client_anonymous, "/login/", payload, status.HTTP_200_OK)
#     self.assertEqual(token_key_1, "testing_e2e_token")
#     self.assertTrue(Token.objects.filter(key="testing_e2e_token", user=self.user_authorized_1).exists())
#     self.assertEqual(Token.objects.filter(user=self.user_authorized_1).count(), 1)

#     # Second login
#     token_key_2 = tests_helpers.client_post(self, self.client_anonymous, "/login/", payload, status.HTTP_200_OK)
#     self.assertEqual(token_key_2, "testing_e2e_token")
#     self.assertEqual(token_key_1, token_key_2) # Should be the same token
#     self.assertEqual(Token.objects.filter(user=self.user_authorized_1).count(), 1)

#     # Try to use the token (should succeed)
#     client_with_token = APIClient()
#     client_with_token.credentials(HTTP_AUTHORIZATION=f'Token {token_key_1}')
#     tests_helpers.client_get(self, client_with_token, "/profile/", status.HTTP_200_OK)
