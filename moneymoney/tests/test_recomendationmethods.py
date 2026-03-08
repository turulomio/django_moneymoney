from rest_framework import status
from moneymoney.reusing import tests_helpers


def test_RecomendationMethods(self):
    """
        Test the RecomendationMethods view returns a list of recommendation methods.
    """
    response = tests_helpers.client_get(self, self.client_authorized_1, "/recomendationmethods/", status.HTTP_200_OK)
    
    self.assertIsInstance(response, list)
    self.assertTrue(len(response) > 0) # Expect at least one recommendation method
    self.assertIn("id", response[0])
    self.assertIn("name", response[0])
