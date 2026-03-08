from moneymoney import models
from moneymoney.reusing import tests_helpers
from rest_framework import status
from pydicts import lod


def test_StrategiesFastOperations(self):
    # Opens account
    tests_helpers.client_post(self, self.client_authorized_1, "/api/accountsoperations/",  models.Accountsoperations.post_payload(concepts=self.hurl_concepts_oa, amount=999999), status.HTTP_201_CREATED)

    # Create a FO strategy
    dict_strategy_fos=tests_helpers.client_post(self, self.client_authorized_1, "/api/strategies_fastoperations/",  models.StrategiesFastOperations.post_payload(strategy=models.Strategies.post_payload(name="FOS", type=models.StrategiesTypes.FastOperations), accounts=["http://testserver/api/accounts/4/"]), status.HTTP_201_CREATED)

    tests_helpers.client_post(self, self.client_authorized_1, "/api/accountsoperations/",  models.Accountsoperations.post_payload(concepts=self.hurl_concepts_fo, amount=-10, comment="FO"), status.HTTP_201_CREATED)
    tests_helpers.client_post(self, self.client_authorized_1, "/api/accountsoperations/",  models.Accountsoperations.post_payload(concepts=self.hurl_concepts_fo, amount=1010, comment="FO"), status.HTTP_201_CREATED)

    # Get FO strategy detailed view
    strategy_detail=tests_helpers.client_get(self, self.client_authorized_1, f"{dict_strategy_fos['url']}detailed/",  status.HTTP_200_OK)
    self.assertEqual(lod.lod_sum(strategy_detail,"amount"), 1000)

    #Update fos
    dict_strategy_fos=tests_helpers.client_put(self, self.client_authorized_1, dict_strategy_fos["url"],  models.StrategiesFastOperations.post_payload(strategy=models.Strategies.post_payload(name="FOS Updated", type=models.StrategiesTypes.FastOperations), accounts=["http://testserver/api/accounts/4/"]), status.HTTP_200_OK)
    self.assertEqual(dict_strategy_fos["strategy"]["name"], "FOS Updated")

    # Get a created StrategiesFastOperations
    dict_strategy_fos=tests_helpers.client_get(self, self.client_authorized_1, dict_strategy_fos["url"], status.HTTP_200_OK)
    self.assertEqual(dict_strategy_fos["strategy"]["name"], "FOS Updated")

    # Creates a strategy empty directly should fail, due to it redirect to StrategiesFastOperations and needs accounts ...
    tests_helpers.client_post(self, self.client_authorized_1, "/api/strategies/",  models.Strategies.post_payload(type=models.StrategiesTypes.FastOperations, name="FOS"), status.HTTP_405_METHOD_NOT_ALLOWED)

    # Update a strategy directly should fail
    tests_helpers.client_put(self, self.client_authorized_1, dict_strategy_fos["strategy"]["url"],  models.Strategies.post_payload(type=models.StrategiesTypes.FastOperations, name="FOS Direct update"), status.HTTP_405_METHOD_NOT_ALLOWED)
    
    # GEt List of strategies
    strategies=tests_helpers.client_get(self, self.client_authorized_1, f"/api/strategies/",  status.HTTP_200_OK)
    self.assertEqual(len(strategies), 1)
    # GEt List of strategies with balance
    strategies=tests_helpers.client_get(self, self.client_authorized_1, f"/api/strategies/withbalance/",  status.HTTP_200_OK)
    self.assertEqual(len(strategies), 1)
    

    # Delete a strategy directly should fail
    tests_helpers.client_delete(self, self.client_authorized_1, dict_strategy_fos["strategy"]["url"], [], status.HTTP_405_METHOD_NOT_ALLOWED)
    
    # Delete a strategy fast operation directly should delete
    after_delete=tests_helpers.client_delete(self, self.client_authorized_1, dict_strategy_fos["url"], [], status.HTTP_204_NO_CONTENT)
    self.assertEqual(len(after_delete), 0)

def test_StrategiesGeneric(self):
    # Creates an investment operation with a quote and an io
    dict_investment=tests_helpers.client_post(self, self.client_authorized_1, "/api/investments/",  models.Investments.post_payload(), status.HTTP_201_CREATED)
    tests_helpers.client_post(self, self.client_authorized_1, "/api/quotes/",  models.Quotes.post_payload(products=dict_investment["products"]), status.HTTP_201_CREATED)

    # Create a Generic strategy
    dict_strategy_generic=tests_helpers.client_post(self, self.client_authorized_1, "/api/strategies_generic/", models.StrategiesGeneric.post_payload(strategy=models.Strategies.post_payload(name="GS", type=models.StrategiesTypes.Generic), investments=[dict_investment["url"]]), status.HTTP_201_CREATED)

    tests_helpers.client_post(self, self.client_authorized_1, "/api/investmentsoperations/", models.Investmentsoperations.post_payload(dict_investment["url"]), status.HTTP_201_CREATED)

    # Get FO strategy detailed view
    strategy_detail=tests_helpers.client_get(self, self.client_authorized_1, f"{dict_strategy_generic['url']}detailed/",  status.HTTP_200_OK)
    first_entry=strategy_detail["entries"][0]
    self.assertEqual(strategy_detail[first_entry]["total_io_current"]["balance_user"], 10000)

    #Update fos
    dict_strategy_generic=tests_helpers.client_put(self, self.client_authorized_1, dict_strategy_generic["url"],  models.StrategiesGeneric.post_payload(strategy=models.Strategies.post_payload(name="GS Updated", type=models.StrategiesTypes.Generic), investments=[dict_investment["url"]]), status.HTTP_200_OK)
    self.assertEqual(dict_strategy_generic["strategy"]["name"], "GS Updated")

    # Get a created StrategiesFastOperations
    dict_strategy_generic=tests_helpers.client_get(self, self.client_authorized_1, dict_strategy_generic["url"], status.HTTP_200_OK)
    self.assertEqual(dict_strategy_generic["strategy"]["name"], "GS Updated")

    # Creates a strategy empty directly should fail, due to it redirect to StrategiesFastOperations and needs accounts ...
    tests_helpers.client_post(self, self.client_authorized_1, "/api/strategies/",  models.Strategies.post_payload(type=models.StrategiesTypes.Generic, name="GS"), status.HTTP_405_METHOD_NOT_ALLOWED)

    # Tries to change type and returns error
    tests_helpers.client_put(self, self.client_authorized_1, dict_strategy_generic["url"],  models.StrategiesGeneric.post_payload(strategy=models.Strategies.post_payload(name="GS Updated", type=models.StrategiesTypes.FastOperations), investments=[dict_investment["url"]]), status.HTTP_400_BAD_REQUEST)

    # Update a strategy directly should fail
    tests_helpers.client_put(self, self.client_authorized_1, dict_strategy_generic["strategy"]["url"],  models.Strategies.post_payload(type=models.StrategiesTypes.Generic, name="GS Direct update"), status.HTTP_405_METHOD_NOT_ALLOWED)
    
    # Delete a strategy directly should fail
    tests_helpers.client_delete(self, self.client_authorized_1, dict_strategy_generic["strategy"]["url"], [], status.HTTP_405_METHOD_NOT_ALLOWED)

    # GEt List of strategies
    strategies=tests_helpers.client_get(self, self.client_authorized_1, f"/api/strategies/",  status.HTTP_200_OK)
    # self.assertTrue("strategiesgeneric" in strategies[0])
    # GEt List of strategies with balance
    strategies=tests_helpers.client_get(self, self.client_authorized_1, f"/api/strategies/withbalance/",  status.HTTP_200_OK)
    self.assertEqual(len(strategies), 1)

    # Delete a strategy directly should fail
    tests_helpers.client_delete(self, self.client_authorized_1, dict_strategy_generic["strategy"]["url"], [], status.HTTP_405_METHOD_NOT_ALLOWED)
    
    # Delete a strategy fast operation directly should delete
    after_delete=tests_helpers.client_delete(self, self.client_authorized_1, dict_strategy_generic["url"], [], status.HTTP_204_NO_CONTENT)
    self.assertEqual(len(after_delete), 0)

def test_StrategiesPairsInSameAccount(self):
    # Create a Pairs strategy with wrong type
    dict_strategy_pairs=tests_helpers.client_post(self, self.client_authorized_1, "/api/strategies_pairsinsameaccount/", models.StrategiesPairsInSameAccount.post_payload(strategy=models.Strategies.post_payload(name="PairS", type=models.StrategiesTypes.Generic)), status.HTTP_400_BAD_REQUEST)

    # Create a Pairs strategy 
    dict_strategy_pairs=tests_helpers.client_post(self, self.client_authorized_1, "/api/strategies_pairsinsameaccount/", models.StrategiesPairsInSameAccount.post_payload(strategy=models.Strategies.post_payload(name="PairS", type=models.StrategiesTypes.PairsInSameAccount)), status.HTTP_201_CREATED)

    # Get FO strategy detailed view
    strategy_detail=tests_helpers.client_get(self, self.client_authorized_1, f"{dict_strategy_pairs['url']}detailed/",  status.HTTP_200_OK)

    #Update fos
    dict_strategy_pairs=tests_helpers.client_put(self, self.client_authorized_1, dict_strategy_pairs["url"],  models.StrategiesPairsInSameAccount.post_payload(strategy=models.Strategies.post_payload(name="GS Updated", type=models.StrategiesTypes.PairsInSameAccount)), status.HTTP_200_OK)
    self.assertEqual(dict_strategy_pairs["strategy"]["name"], "GS Updated")

    # Get a created StrategiesFastOperations
    dict_strategy_pairs=tests_helpers.client_get(self, self.client_authorized_1, dict_strategy_pairs["url"], status.HTTP_200_OK)
    self.assertEqual(dict_strategy_pairs["strategy"]["name"], "GS Updated")

    # Creates a strategy empty directly should fail, due to it redirect to StrategiesFastOperations and needs accounts ...
    tests_helpers.client_post(self, self.client_authorized_1, "/api/strategies/",  models.Strategies.post_payload(type=models.StrategiesTypes.Generic, name="GS"), status.HTTP_405_METHOD_NOT_ALLOWED)

    # Tries to change type and returns error

    tests_helpers.client_put(self, self.client_authorized_1, dict_strategy_pairs["url"],  models.StrategiesPairsInSameAccount.post_payload(strategy=models.Strategies.post_payload(name="GS Updated", type=models.StrategiesTypes.Generic)), status.HTTP_400_BAD_REQUEST)

    # Update a strategy directly should fail
    tests_helpers.client_put(self, self.client_authorized_1, dict_strategy_pairs["strategy"]["url"],  models.Strategies.post_payload(type=models.StrategiesTypes.Generic, name="GS Direct update"), status.HTTP_405_METHOD_NOT_ALLOWED)
    
    # Delete a strategy directly should fail
    tests_helpers.client_delete(self, self.client_authorized_1, dict_strategy_pairs["strategy"]["url"], [], status.HTTP_405_METHOD_NOT_ALLOWED)

    # GEt List of strategies
    strategies=tests_helpers.client_get(self, self.client_authorized_1, f"/api/strategies/",  status.HTTP_200_OK)
    self.assertEqual(len(strategies), 1)
    # GEt List of strategies with balance
    strategies=tests_helpers.client_get(self, self.client_authorized_1, f"/api/strategies/withbalance/",  status.HTTP_200_OK)
    self.assertEqual(len(strategies), 1)

    # Delete a strategy directly should fail
    tests_helpers.client_delete(self, self.client_authorized_1, dict_strategy_pairs["strategy"]["url"], [], status.HTTP_405_METHOD_NOT_ALLOWED)
    
    # Delete a strategy fast operation directly should delete
    after_delete=tests_helpers.client_delete(self, self.client_authorized_1, dict_strategy_pairs["url"], [], status.HTTP_204_NO_CONTENT)
    self.assertEqual(len(after_delete), 0)


def test_StrategiesProductsRange(self):
    # Creates an investment operation with a quote and an io
    dict_investment=tests_helpers.client_post(self, self.client_authorized_1, "/api/investments/",  models.Investments.post_payload(), status.HTTP_201_CREATED)
    tests_helpers.client_post(self, self.client_authorized_1, "/api/quotes/",  models.Quotes.post_payload(products=dict_investment["products"]), status.HTTP_201_CREATED)
    # Create a Pairs strategy with wrong type
    dict_strategy_pr=tests_helpers.client_post(self, self.client_authorized_1, "/api/strategies_productsrange/", models.StrategiesProductsRange.post_payload(strategy=models.Strategies.post_payload(name="PRS", type=models.StrategiesTypes.Generic), investments=[dict_investment["url"]]), status.HTTP_400_BAD_REQUEST)

    # Create a Pairs strategy 
    dict_strategy_pr=tests_helpers.client_post(self, self.client_authorized_1, "/api/strategies_productsrange/", models.StrategiesProductsRange.post_payload(strategy=models.Strategies.post_payload(name="PRS", type=models.StrategiesTypes.Ranges), investments=[dict_investment["url"]]), status.HTTP_201_CREATED)

    # Get FO strategy detailed view
    strategy_detail=tests_helpers.client_get(self, self.client_authorized_1, f"{dict_strategy_pr['url']}detailed/",  status.HTTP_200_OK)

    #Update fos
    dict_strategy_pr=tests_helpers.client_put(self, self.client_authorized_1, dict_strategy_pr["url"],  models.StrategiesProductsRange.post_payload(strategy=models.Strategies.post_payload(name="PRS Updated", type=models.StrategiesTypes.Ranges), investments=[dict_investment["url"]]), status.HTTP_200_OK)
    self.assertEqual(dict_strategy_pr["strategy"]["name"], "PRS Updated")

    # Get a created StrategiesProductsRange
    dict_strategy_pr=tests_helpers.client_get(self, self.client_authorized_1, dict_strategy_pr["url"], status.HTTP_200_OK)
    self.assertEqual(dict_strategy_pr["strategy"]["name"], "PRS Updated")

    # Creates a strategy empty directly should fail, due to it redirect to StrategiesFastOperations and needs accounts ...
    tests_helpers.client_post(self, self.client_authorized_1, "/api/strategies/",  models.Strategies.post_payload(type=models.StrategiesTypes.Ranges, name="PRS"), status.HTTP_405_METHOD_NOT_ALLOWED)

    # Tries to change type and returns error
    tests_helpers.client_put(self, self.client_authorized_1, dict_strategy_pr["url"],  models.StrategiesPairsInSameAccount.post_payload(strategy=models.Strategies.post_payload(name="GS Updated", type=models.StrategiesTypes.Generic)), status.HTTP_400_BAD_REQUEST)

    # Update a strategy directly should fail
    tests_helpers.client_put(self, self.client_authorized_1, dict_strategy_pr["strategy"]["url"],  models.Strategies.post_payload(type=models.StrategiesTypes.Generic, name="GS Direct update"), status.HTTP_405_METHOD_NOT_ALLOWED)
    
    # Delete a strategy directly should fail
    tests_helpers.client_delete(self, self.client_authorized_1, dict_strategy_pr["strategy"]["url"], [], status.HTTP_405_METHOD_NOT_ALLOWED)

    # GEt List of strategies
    strategies=tests_helpers.client_get(self, self.client_authorized_1, f"/api/strategies/",  status.HTTP_200_OK)
    self.assertEqual(len(strategies), 1)

    # GEt List of strategies with balance
    strategies=tests_helpers.client_get(self, self.client_authorized_1, f"/api/strategies/withbalance/",  status.HTTP_200_OK)
    self.assertEqual(len(strategies), 1)

    # Delete a strategy directly should fail
    tests_helpers.client_delete(self, self.client_authorized_1, dict_strategy_pr["strategy"]["url"], [], status.HTTP_405_METHOD_NOT_ALLOWED)
    
    # Delete a strategy fast operation directly should delete
    after_delete=tests_helpers.client_delete(self, self.client_authorized_1, dict_strategy_pr["url"], [], status.HTTP_204_NO_CONTENT)
    self.assertEqual(len(after_delete), 0)
