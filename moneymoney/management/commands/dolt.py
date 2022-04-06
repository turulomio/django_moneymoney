from django.core.management.base import BaseCommand 
from moneymoney.reusing.text_inputs import input_boolean, input_string
from os import system, makedirs, chdir, remove, path

class Command(BaseCommand):
    help = 'Installs dolt, launches sql console, makes commit, makes push, makes dump in moneymoney/data/'

    def add_arguments(self, parser):
        pass
        
    def reinstall_dolt(self):
        makedirs("dolt", exist_ok=True)
        chdir("dolt")
        if path.exists("dolt-linux-amd64.tar.gz"):
            remove("dolt-linux-amd64.tar.gz")
            
        system("wget https://github.com/dolthub/dolt/releases/latest/download/dolt-linux-amd64.tar.gz")
        system("tar xvfz dolt-linux-amd64.tar.gz")
        system("dolt-linux-amd64/bin/dolt clone turulomio/dolthub_money")
        chdir("..")
        
        
    def handle(self, *args, **options):
        makedirs("moneymoney/data/", exist_ok=True)
        # from whichcraft import which
        if path.exists("dolt") is True:            
            if input_boolean("Dolt seems to be installed. Do you want to reinstall it ?", default="F"):
                self.reinstall_dolt()
        else:
            self.reinstall_dolt()
            
        chdir("dolt/dolthub_money")
        system("../dolt-linux-amd64/bin/dolt pull")
        system("../dolt-linux-amd64/bin/dolt sql")
        commit_messages=input_string("If you want to make a commit, enter a comment. Empty to continue", default="")
        if commit_messages!="":
            system(f"../dolt-linux-amd64/bin/dolt commit -am '{commit_messages}'")
            system("../dolt-linux-amd64/bin/dolt push")            
        system("../dolt-linux-amd64/bin/dolt dump -r json -f --directory=../../moneymoney/data")            
        
        chdir("../..")

