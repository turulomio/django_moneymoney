from moneymoney.reusing.tests_helpers import TestModel, td_string, td_timezone, td_integer, td_decimal

    
class tmBanks(TestModel):
    catalog=False
    private=True
    examples=[
        {
            "name":td_string(), 
            "active": True, 
        }, 
    ]    
    
    
class tmOperationstypes(TestModel):
    catalog=True
    private=False
    examples=[
        {
            "name":td_string(),
        }, 
    ]
    
    @classmethod
    def url_model_name(cls):
        return "operationstypes"
    
    
class tmConcepts(TestModel):
    catalog=False
    private=True
    examples=[
        {
            "name":td_string(), 
            "operationstypes":tmOperationstypes.hlu(1), 
            "editable": True, 
        }, 
    ]
    
        
class tmAccounts(TestModel):
    catalog=False
    private=True
    examples=[
        {
            "name":td_string(), 
            "banks": tmBanks, 
            "active": True, 
            "number": "01234567890", 
            "currency":"EUR", 
            "decimals":2, 
        }, 
    ]
        
        
class tmAccountsoperations(TestModel):
    catalog=False
    private=True
    examples=[
        {
            "concepts": tmConcepts.hlu(1), 
            "operationstypes": tmOperationstypes.hlu(2), 
            "amount": 12.23, 
            "comment": td_string(), 
            "accounts": tmAccounts, 
            "datetime": td_timezone(), 
        }, 
    ]
    
    
    @classmethod
    def url_model_name(cls):
        return "accountsoperations"
