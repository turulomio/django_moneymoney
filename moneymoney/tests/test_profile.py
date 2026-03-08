from rest_framework import status
from moneymoney import models
from moneymoney.reusing import tests_helpers
from django.contrib.auth.models import User


def test_Profile(self):
    """
        Test created users has its profile automatically generated,
        and also tests GET and PUT operations on the profile.
    """

    # Test automatic profile generation
    a = User()
    a.username = "me"
    a.save()
    self.assertNotEqual(a, None)
    self.assertNotEqual(a.profile, None) # Ensure 'a' also has a profile

    self.assertNotEqual(self.user_authorized_1.profile, None)
    self.assertNotEqual(self.user_authorized_2.profile, None)
    self.assertNotEqual(self.user_catalog_manager.profile, None)

    # Test adding favorites
    p = models.Products.objects.get(pk=79329)
    self.user_authorized_1.profile.favorites.add(p)
    self.user_authorized_1.profile.save()
    self.assertEqual(self.user_authorized_1.profile.favorites.count(), 1)

    # Test PUT request to update profile
    current_profile_data = tests_helpers.client_get(self, self.client_authorized_1, "/profile/", status.HTTP_200_OK)
    new_annual_gains_target = 15.5
    current_profile_data["annual_gains_target"] = new_annual_gains_target
    
    updated_profile = tests_helpers.client_put(self, self.client_authorized_1, "/profile/", current_profile_data, status.HTTP_200_OK)
    self.assertEqual(updated_profile["annual_gains_target"], new_annual_gains_target)
