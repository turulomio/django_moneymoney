
from enum import IntEnum
class eProductType(IntEnum):
    """
        IntEnum permite comparar 1 to eProductType.Share
    """
    Share=1
    Fund=2
    Index=3
    ETF=4
    Warrant=5
    Currency=6
    PublicBond=7
    PensionPlan=8
    PrivateBond=9
    Deposit=10
    Account=11
    CFD=12
    Future=13
    
class eOHCLDuration:
    Day=1
    Week=2
    Month=3
    Year=4

## Operation tipes
class eOperationType:
    Expense=1
    Income=2
    Transfer=3
    SharesPurchase=4
    SharesSale=5
    SharesAdd=6
    CreditCardBilling=7
    TransferFunds=8
    TransferSharesOrigin=9
    TransferSharesDestiny=10
    DerivativeManagement=11
    FastOperations=12
    
class eTickerPosition(IntEnum):
    """It's the number to access to a python list,  not to postgresql. In postgres it will be +1"""
    Yahoo=0
    Morningstar=1
    Google=2
    QueFondos=3
    InvestingCom=4
    
    def postgresql(etickerposition):
        return etickerposition.value+1
        
    ## Returns the number of atributes
    def length():
        return 5

#
#class eComment:
#    InvestmentOperation=10000
#    Dividend=10004
#    AccountTransferOrigin=10001
#    AccountTransferDestiny=10002
#    AccountTransferOriginCommission=10003
#    CreditCardBilling=10005
#    CreditCardRefund=10006

## System concepts tipified
class eConcept:
    OpenAccount=1
    TransferOrigin=4
    TransferDestiny=5
    TaxesReturn=6
    BuyShares=29
    SellShares=35
    TaxesPayment=37
    BankCommissions=38
    Dividends=39
    CreditCardBilling=40
    AddShares=43
    AssistancePremium=50
    CommissionCustody=59
    DividendsSaleRights=62
    BondsCouponRunPayment=63
    BondsCouponRunIncome=65
    BondsCoupon=66
    CreditCardRefund=67
    DerivativesAdjustment=68
    DerivativesGuarantee=70
    DerivativesCommission=72
    DerivativesSwap=77
    FastInvestmentOperations=74
    RolloverPaid=75
    RolloverReceived=76
    
    @staticmethod
    def dividends():
        """
            Return a list of integers (types) with all Concepts used in Investiments dividends
        """
        return [
            eConcept.Dividends, 
            eConcept.AssistancePremium, 
            eConcept.DividendsSaleRights, 
            eConcept.BondsCoupon, 
            eConcept.BondsCouponRunIncome, 
            eConcept.BondsCouponRunPayment, 
        ]

## Sets if a Historical Chart must adjust splits or dividends with splits or do nothing
class eHistoricalChartAdjusts:
    ## Without splits nor dividens
    NoAdjusts=0
    ## WithSplits
    Splits=1
    ##With splits and dividends
    SplitsAndDividends=2#Dividends with splits.        


class eLeverageType:
    Variable=-1
    NotLeveraged=1
    X2=2
    X3=3
    X4=4
    X5=5
    X10=10
    X20=20
    X25=25
    X50=50
    X100=100
    X200=200
    X500=500
    X1000=1000

class eMoneyCurrency:
    Product=1
    Account=2
    User=3

class eProductStrategy:
    Call=1
    Put=2
    Inline=3
