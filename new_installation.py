
dropdb -U postgres moneymoney_deleteme; createdb -U postgres moneymoney_deleteme
python manage.py database_update --settings django_moneymoney.presettings

