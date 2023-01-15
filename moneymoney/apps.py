from django.apps import AppConfig



class MoneyMoneyConfig(AppConfig):
    name = 'moneymoney'





    # add this
    def ready(self):
        print("Activating signals...")
        import moneymoney.signals  # noqa
