from django.apps import AppConfig

class MoneyMoneyConfig(AppConfig):
    name = 'moneymoney'

    def ready(self):
        print("Activating signals...")
        import moneymoney.signals
