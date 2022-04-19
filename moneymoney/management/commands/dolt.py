from django.core.management.base import BaseCommand 
from moneymoney.reusing.text_inputs import input_boolean, input_string
from os import system, makedirs, chdir, path
from shutil import rmtree

class Command(BaseCommand):
    help = 'Installs dolt, launches sql console, makes commit, makes push, makes dump in moneymoney/data/'

    def add_arguments(self, parser):
        pass
        
    def reinstall_dolt(self):
        makedirs("dolt", exist_ok=True)
        chdir("dolt")
        system("dolt clone turulomio/dolthub_money")
        chdir("..")
        
        
    def handle(self, *args, **options):
        makedirs("moneymoney/data/", exist_ok=True)
        # from whichcraft import which
        if path.exists("dolt/dolthub_money") is True:            
            if input_boolean("Dolt repository seems to be already cloned. Do you want to reinstall it ?", default="F"):
                rmtree("dolt/dolthub_money")
                self.reinstall_dolt()
        else:
            self.reinstall_dolt()
            
        chdir("dolt/dolthub_money")
        system("dolt pull")
        system("dolt sql")
        system("dolt diff")
        commit_messages=input_string("If you want to make a commit, enter a comment. Empty to continue", default="")
        if commit_messages!="":
            system(f"dolt commit -am '{commit_messages}'")
            system("dolt push")            
        system("dolt dump -r json -f --directory=../../moneymoney/data")            
        
        chdir("../..")

