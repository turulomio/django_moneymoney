from sys import argv
from moneymoney.reusing.github import download_from_github
from moneymoney.reusing.file_functions import replace_in_file

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
        download_from_github("turulomio", "reusingcode", "django/responses_json.py", "moneymoney/reusing")
        download_from_github("turulomio", "reusingcode", "django/request_casting.py", "moneymoney/reusing")
        download_from_github("turulomio", "reusingcode", "python/call_by_name.py", "moneymoney/reusing")
        download_from_github("turulomio", "reusingcode", "python/casts.py", "moneymoney/reusing")
        download_from_github("turulomio", "reusingcode", "python/connection_pg.py", "moneymoney/reusing")
        download_from_github("turulomio", "reusingcode", "python/currency.py", "moneymoney/reusing")
        download_from_github("turulomio", "reusingcode", "python/decorators.py", "moneymoney/reusing")
        download_from_github("turulomio", "reusingcode", "python/file_functions.py", "moneymoney/reusing")
        download_from_github("turulomio", "reusingcode", "python/percentage.py", "moneymoney/reusing")
        download_from_github("turulomio", "reusingcode", "python/lineal_regression.py", "moneymoney/reusing")
        download_from_github("turulomio", "reusingcode", "python/github.py", "moneymoney/reusing")
        download_from_github("turulomio", "reusingcode", "python/datetime_functions.py", "moneymoney/reusing")
        download_from_github("turulomio", "reusingcode", "python/sqlparser.py", "moneymoney/reusing")
        download_from_github("turulomio", "reusingcode", "python/text_inputs.py", "moneymoney/reusing")
        download_from_github("turulomio", "reusingcode", "python/libmanagers.py", "moneymoney/reusing")

    replace_in_file("moneymoney/reusing/libmanagers.py", "from call_by_name", "from .call_by_name")
    replace_in_file("moneymoney/reusing/libmanagers.py", "from datetime_functions", "from .datetime_functions")
