from rest_framework import status
from moneymoney.reusing import tests_helpers

def test_Statistics_view_basic(self):
    """
    Test that the Statistics view returns a 200 OK status and a dictionary.
    """
    response = tests_helpers.client_get(self, self.client_authorized_1, "/statistics/", status.HTTP_200_OK)
    self.assertIsInstance(response, list)
    # Further assertions could be added here to check the structure or content
    # of the statistics data, once the expected output is known.
    # For example:
    # self.assertIn("total_invested", response)
    # self.assertIn("total_gains", response)
