from django.utils.translation import gettext_lazy as _

from moneymoney.models import Products,  Quotes

from csv import reader
#from logging import debug
#from datetime import date
from io import StringIO
#from xulpymoney.objects.quote import Quote
#from xulpymoney.objects.ohcl import  OHCLDaily
from moneymoney.reusing.casts import string2decimal
from moneymoney.reusing.datetime_functions import dtaware, string2date, string2dtaware
#from monemoney.models import eTickerPosition

class InvestingCom:
    def __init__(self, request, filename_in_memory, product=None):
        self.filename_in_memory=filename_in_memory
        self.request=request
        self.product=product
        self.columns=self.get_number_of_csv_columns()
        self.log=[]
        
    def get(self):
        if self.product==None: #Several products
            if self.columns==8:
#                messages.info(self.request,"append_from_default")
                return self.append_from_default()
            elif self.columns==39:
                self.log.append(_("Adding quotes from Investing.com portfolio"))
                return self.append_from_portfolio()
            else:
#                messages.error(self.request,"The number of columns doesn't match: {}".format(self.columns))
                return "NUMBER OF COLUMNS DOESN'T MATCH"
        else:
#            messages.info(self.request, "append_from_historical")
            return self.append_from_historical()
            
    def get_csv_object_seeking(self):
        self.filename_in_memory.seek(0)
        csv_object=reader(StringIO(self.filename_in_memory.read().decode('utf-8')))
        return csv_object

    def get_number_of_csv_columns(self):
        for row in self.get_csv_object_seeking():
            return len(row)
        return -1
        
    ## Used by InvestingCom, to load indexes components, it has 8 columns
    ## 0 Índice 
    ## 1 Símbolo    
    ## 2 Último 
    ## 3 Máximo append_from_portfolio
    ## 4 Mínimo 
    ## 5 Var
    ## 6 % Var. 
    ## 7 Hora
    def append_from_default(self):
        pass
#        with open(self.filename) as csv_file:
#            csv_reader = reader(csv_file, delimiter=',')
#            line_count = 0
#            for row in csv_reader:
#                if line_count >0:#Ignores headers line
#                    products=self.mem.data.products.find_all_by_ticker(row[1], eTickerPosition.InvestingCom)
#                    print(row[1], len(products))
#                    if len(products)==0:
#                        print(_(f"Product with InvestingCom ticker {row[1]} wasn't found"))
#                    for product in products:
#                        if row[7].find(":")==-1:#It's a date
#                            try:
#                                quote=Quote(self.mem)
#                                quote.product=product
#                                date_=string2date(row[7], "DD/MM")
#                                quote.datetime=dtaware(date_,quote.product.stockmarket.closes,self.mem.localzone_name)#Without 4 microseconds becaouse is not a ohcl
#                                quote.quote=string2decimal(row[2])
#                                self.append(quote)
#                            except:
#                                debug("Error parsing "+ str(row))
#                        else: #It's an hour
#                            try:
#                                quote=Quote(self.mem)
#                                quote.product=product
#                                time_=string2time(row[7], "HH:MM:SS")
#                                quote.datetime=dtaware(date.today(), time_, self.mem.localzone_name)
#                                quote.quote=string2decimal(row[3])
#                                self.append(quote)
#                            except:
#                                debug("Error parsing "+ str(row))
#                line_count += 1
#        print("Added {} quotes from {} CSV lines".format(self.length(), line_count))
        
    ## 0 Nombre 
    ## 1 Símbolo    
    ## 2 Mercado    
    ## 3 Último
    ## 4    Compra  
    ## 5 Venta  
    ## 6 Horario ampliado   
    ## 7 Horario ampliado (%)   
    ## 8 Apertura   
    ## 9 Anterior   
    ## 10 Máximo    
    ## 11 Mínimo    
    ## 12 Var.  
    ## 13 % var.    
    ## 14 Vol.  
    ## 15 Fecha próx. resultados    
    ## 16  Hora Cap. mercado    Ingresos    Vol. promedio (3m)  BPA PER Beta    Dividendo   Rendimiento 5 minutos   15 minutos  30 minutos  1 hora  5 horas Diario  Semanal Mensual Diario  Semanal Mensual Anual   1 año   3 años
    ## It has 39 columns
    def append_from_portfolio(self):
        r=[]
        line_count = 0
        quotes_count = 0
        for row in self.get_csv_object_seeking():
            if line_count >0:#Ignores headers line
                if row[2]=="":
                    products=Products.objects.raw('SELECT products.* FROM products where tickers[5]=%s', (f"{row[1]}", ))
                    code=f"{row[1]}"
                else:
                    products=Products.objects.raw('SELECT products.* FROM products where tickers[5]=%s', (f"{row[1]}#{row[2]}", ))
                    code=f"{row[1]}#{row[2]}"
                    
                if len(products)==0:
                    d={"product":None,   "code":code,  "log": "Product wasn't found"}
                    
                    
                for product in products:
                    d={"product": product.fullName(),   "code":code}
                    if row[16].find(":")==-1:#It's a date
                        try:
                            quote=Quotes()
                            quote.products=product
                            date_=string2date(row[16], "DD/MM")
                            quote.datetime=dtaware(date_, product.stockmarkets.closes, product.stockmarkets.zone)#Without 4 microseconds becaouse is not a ohcl
                            quote.quote=string2decimal(row[3])
                            quotes_count=quotes_count+1
                            d["log"]=quote.modelsave()
                        except:
                            d["log"]="Error parsing date"+ str(row)
                    else: #It's an hour
                        try:
                            quote=Quotes()
                            quote.products=product
                            quote.datetime=string2dtaware(row[16],"%H:%M:%S", self.request.globals["mem__localzone"])
                            quote.quote=string2decimal(row[3])
                            quotes_count=quotes_count+1
                            d["log"]=quote.modelsave()
                        except:
                            d["log"]="Error parsing hour" + str(row)
                    r.append(d)
            line_count += 1
        return r

    ## Imports data from a CSV file with this struct. It has 6 columns
    ## "Fecha","Último","Apertura","Máximo","Mínimo","Vol.","% var."
    ## "22.07.2019","10,074","10,060","10,148","9,987","10,36M","-0,08%"
    def append_from_historical(self):
        pass
#            with open(self.filename) as csv_file:
#                csv_reader = reader(csv_file, delimiter=',')
#                line_count = 0
#                for row in csv_reader:
#                    if line_count >0:#Ignores headers line
#                        try:
#                            ohcl=OHCLDaily(self.mem)
#                            ohcl.product=self.product
#                            ohcl.date=string2date(row[0], "DD.MM.YYYY")
#                            ohcl.close=string2decimal(row[1])
#                            ohcl.open=string2decimal(row[2])
#                            ohcl.high=string2decimal(row[3])
#                            ohcl.low=string2decimal(row[4])
#                            for quote in ohcl.generate_4_quotes():
#                                self.append(quote)
#                        except:
#                            debug("Error parsing" + str(row))
#                    line_count += 1
#            print("Added {} quotes from {} CSV lines".format(self.length(), line_count))
