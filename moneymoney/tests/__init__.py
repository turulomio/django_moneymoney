from django.contrib.auth.models import User
from rest_framework.test import APIClient, APITestCase
from moneymoney.reusing.tests_dinamic_methods import add_method_to_this_class_dinamically

from django.db import transaction, connection
from django.test.utils import CaptureQueriesContext

from logging import getLogger, ERROR
logger = getLogger('django.request')
logger.setLevel(ERROR) # This will suppress INFO and WARNING

class assert_max_queries(CaptureQueriesContext):
    def __init__(self, test_case, max_queries):
        self.test_case = test_case
        self.max_queries = max_queries
        super().__init__(connection)

    def __exit__(self, exc_type, exc_value, traceback):
        super().__exit__(exc_type, exc_value, traceback)
        if exc_type is not None:
            return

        num_queries = len(self)

        if num_queries > self.max_queries:
            total_time = 0
            strqueries = ""
            for query in self.captured_queries:
                total_time += float(query['time'])
                strqueries += f"[{query['time']}s] {query['sql']}\n\n"

            msg = (
                f"Queries:\n{strqueries}"
                f"Exceeded query limit. Executed {num_queries} queries in {total_time:.3f}s, "
                f"but the limit was {self.max_queries}.\n"
            )
            self.test_case.fail(msg)

class MoneyMoneyAPITestCase(APITestCase):
    """
    Base class for API tests.
    It sets up fixtures and authenticated clients once for all inheriting test classes.
    """
    fixtures = ["all.json","test_users.json"]

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs )   
        # add_methodtypes_to_this_object_dinamically(self)

    @classmethod
    def setUpClass(cls):
        """
        Set up non-database specific resources once for all test classes.
        """
        super().setUpClass()


        cls.user_authorized_1 = User.objects.get(username='authorized_1')
        cls.user_authorized_2 = User.objects.get(username='authorized_2')
        cls.user_catalog_manager = User.objects.get(username='catalog_manager')

        cls.client_authorized_1 = APIClient()
        cls.client_authorized_1.force_authenticate(user=cls.user_authorized_1)
        cls.client_authorized_1.user = cls.user_authorized_1

        cls.client_authorized_2 = APIClient()
        cls.client_authorized_2.force_authenticate(user=cls.user_authorized_2)
        cls.client_authorized_2.user = cls.user_authorized_2

        cls.client_anonymous = APIClient()
        cls.client_anonymous.user = None

        cls.client_catalog_manager = APIClient()
        cls.client_catalog_manager.force_authenticate(user=cls.user_catalog_manager)
        cls.client_catalog_manager.user = cls.user_catalog_manager


add_method_to_this_class_dinamically(MoneyMoneyAPITestCase, "moneymoney/tests", "test_*.py")