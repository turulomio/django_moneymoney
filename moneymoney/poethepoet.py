from sys import argv
from moneymoney.reusing.github import download_from_github
from os import system

def reusing():
    """
        Actualiza directorio reusing
        poe reusing
        poe reusing --local
    """
    local=False
    if len(argv)==2 and argv[1]=="--local":
        local=True
        print("Update code in local without downloading was selected with --local")
    if local==False:
        download_from_github("turulomio", "reusingcode", "python/decorators.py", "moneymoney/reusing")
        download_from_github("turulomio", "reusingcode", "python/file_functions.py", "moneymoney/reusing")
        download_from_github("turulomio", "reusingcode", "python/github.py", "moneymoney/reusing")
        download_from_github("turulomio", "django_calories_tracker", "calories_tracker/tests_helpers.py", "moneymoney/reusing")


def cypress_test_server():
    print("- Dropping test_xulpymoney database...")
    system("dropdb -U postgres -h 127.0.0.1 test_xulpymoney")
    print("- Launching python manage.py test_server with user 'test' and password 'test'")
    system("python manage.py testserver moneymoney/fixtures/all.json moneymoney/fixtures/test_server.json --addrport 8004")

def cypress_test_server_for_github_actions():
    print("- Launching python manage.py test_server with user 'test' and password 'test'")
    system("python manage.py testserver moneymoney/fixtures/all.json moneymoney/fixtures/test_server.json --addrport 8004")
