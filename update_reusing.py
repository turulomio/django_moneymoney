from argparse import ArgumentParser
from money.reusing.github import download_from_github
from os import remove

def replace_in_file(filename, s, r):
    data=open(filename,"r").read()
    remove(filename)
    data=data.replace(s,r)
    f=open(filename, "w")
    f.write(data)
    f.close()

parser=ArgumentParser()
parser.add_argument('--local', help='Parses files without download', action="store_true", default=False)
args=parser.parse_args()      

if args.local==False:
    download_from_github("turulomio", "reusingcode", "python/call_by_name.py", "money/reusing")
    download_from_github("turulomio", "reusingcode", "python/listdict_functions.py", "money/reusing")
    download_from_github("turulomio", "reusingcode", "django/tabulator.py", "money/reusing")
    download_from_github("turulomio", "reusingcode", "django/decorators.py", "money/reusing")
    download_from_github("turulomio", "reusingcode", "python/lineal_regression.py", "money/reusing")
    download_from_github("turulomio", "reusingcode", "python/casts.py", "money/reusing")
    download_from_github("turulomio", "reusingcode", "python/currency.py", "money/reusing")
    download_from_github("turulomio", "reusingcode", "python/github.py", "money/reusing")
    download_from_github("turulomio", "reusingcode", "python/datetime_functions.py", "money/reusing")
    download_from_github("turulomio", "reusingcode", "python/text_inputs.py", "money/reusing")
    download_from_github("turulomio", "reusingcode", "django/templatetags/mymenu.py", "money/templatetags")
    download_from_github("turulomio", "reusingcode", "js/component.ajaxbutton.js", "money/static/js")
    download_from_github("turulomio", "reusingcode", "js/component.yearmonthpicker.js", "money/static/js")
    download_from_github("turulomio", "reusingcode", "js/component.yearpicker.js", "money/static/js")
    download_from_github("turulomio", "reusingcode", "vue/components/ChartPie.js", "money/static/js/vuecomponents/")
    download_from_github("turulomio", "reusingcode", "vue/components/MyDatePicker.js", "money/static/js/vuecomponents/")

replace_in_file("money/reusing/casts.py", "from currency", "from .currency")
replace_in_file("money/reusing/casts.py", "from percentage", "from .percentage")
replace_in_file("money/reusing/listdict_functions.py", "from casts", "from .casts")

