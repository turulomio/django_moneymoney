from sys import argv
from moneymoney.reusing.github import download_from_github
#from moneymoney.reusing.file_functions import replace_in_file

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
        download_from_github("turulomio", "reusingcode", "django/connection_dj.py", "moneymoney/reusing")
        download_from_github("turulomio", "reusingcode", "python/decorators.py", "moneymoney/reusing")
        download_from_github("turulomio", "reusingcode", "python/file_functions.py", "moneymoney/reusing")
        download_from_github("turulomio", "reusingcode", "python/github.py", "moneymoney/reusing")
        download_from_github("turulomio", "django_calories_tracker", "calories_tracker/tests_helpers.py", "moneymoney/reusing")

