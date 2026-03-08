from moneymoney import models


def test_Stockmarkets(self):
    o=models.Stockmarkets.objects.get(pk=1)
    str(o)
    o.dtaware_closes(self.today)
    o.dtaware_closes_futures(self.today)
    o.dtaware_today_closes()
    o.dtaware_today_closes_futures()
    o.dtaware_starts(self.today)
    o.dtaware_today_starts()
    o.estimated_datetime_for_daily_quote()
    o.estimated_datetime_for_intraday_quote()
    o.estimated_datetime_for_intraday_quote(delay=True)
        