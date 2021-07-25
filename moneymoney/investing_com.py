from django.contrib import messages
from django.utils.translation import ugettext_lazy as _

from money.models import Products,  Quotes

from csv import reader
from logging import debug
from datetime import date
from io import StringIO
from xulpymoney.objects.quote import Quote
from xulpymoney.objects.ohcl import  OHCLDaily
from xulpymoney.casts import string2decimal
from xulpymoney.datetime_functions import dtaware, string2date, string2dtaware, string2time
from xulpymoney.libxulpymoneytypes import eTickerPosition

class InvestingCom:
    def __init__(self, request, filename_in_memory, product=None):
        self.filename_in_memory=filename_in_memory
        self.request=request
        self.product=product
        self.columns=self.get_number_of_csv_columns()
        self.log=[]
        if self.product==None: #Several products
            if self.columns==8:
                messages.info(self.request,"append_from_default")
                self.append_from_default()
            elif self.columns==39:
                self.log.append(_("Adding quotes from Investing.com portfolio"))
                self.append_from_portfolio()
            else:
                messages.error(self.request,"The number of columns doesn't match: {}".format(self.columns))
        else:
            messages.info(self.request, "append_from_historical")
            self.append_from_historical()
            
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
    ## 3 Máximo 
    ## 4 Mínimo 
    ## 5 Var
    ## 6 % Var. 
    ## 7 Hora
    def append_from_default(self):
        with open(self.filename) as csv_file:
            csv_reader = reader(csv_file, delimiter=',')
            line_count = 0
            for row in csv_reader:
                if line_count >0:#Ignores headers line
                    products=self.mem.data.products.find_all_by_ticker(row[1], eTickerPosition.InvestingCom)
                    print(row[1], len(products))
                    if len(products)==0:
                        print(_(f"Product with InvestingCom ticker {row[1]} wasn't found"))
                    for product in products:
                        if row[7].find(":")==-1:#It's a date
                            try:
                                quote=Quote(self.mem)
                                quote.product=product
                                date_=string2date(row[7], "DD/MM")
                                quote.datetime=dtaware(date_,quote.product.stockmarket.closes,self.mem.localzone_name)#Without 4 microseconds becaouse is not a ohcl
                                quote.quote=string2decimal(row[2])
                                self.append(quote)
                            except:
                                debug("Error parsing "+ str(row))
                        else: #It's an hour
                            try:
                                quote=Quote(self.mem)
                                quote.product=product
                                time_=string2time(row[7], "HH:MM:SS")
                                quote.datetime=dtaware(date.today(), time_, self.mem.localzone_name)
                                quote.quote=string2decimal(row[3])
                                self.append(quote)
                            except:
                                debug("Error parsing "+ str(row))
                line_count += 1
        print("Added {} quotes from {} CSV lines".format(self.length(), line_count))
        
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
        line_count = 0
        quotes_count = 0
        for row in self.get_csv_object_seeking():
            if line_count >0:#Ignores headers line
#                ## Casos especiales por ticker repetido se compara con más información.
#                if row[1]=="DE30" and row[2]=="DE":
#                    products=[Products.objects.get(id=78094),]#DAX 30
#                elif row [1]=="DE30" and row[2]=="Eurex":
#                    products=(Products.objects.get(id=81752),)#CFD DAX 30
#                elif row[1]=="US2000" and row[2]=="P":
#                    products=[Products.objects.get(id=81745),]#RUSELL 2000
#                elif row [1]=="US2000" and row[2]=="ICE":
#                    products=(Products.objects.get(id=81760),)#CFD RUSELL 2000
#                elif "EUR/USD" in row [1]:
#                    products=(Products.objects.get(id=74747),)#EUR/USD
#                elif "Oro al " in row [1]:
#                    products=(Products.objects.get(id=81758), Products.objects.get(id=81757))#CFD ORO
#                else:
                if row[2]=="":
                    products=Products.objects.raw('SELECT products.* FROM products where tickers[5]=%s', (f"{row[1]}", ))
                else:
                    products=Products.objects.raw('SELECT products.* FROM products where tickers[5]=%s', (f"{row[1]}#{row[2]}", ))

                if len(products)==0:
                    self.log.append(_(f"Product with InvestingCom ticker {row[1]} wasn't found"))

                for product in products:
                    if row[16].find(":")==-1:#It's a date
                        try:
                            quote=Quotes()
                            quote.products=product
                            date_=string2date(row[16], "DD/MM")
                            quote.datetime=dtaware(date_, product.stockmarkets.closes, product.stockmarkets.zone)#Without 4 microseconds becaouse is not a ohcl
                            quote.quote=string2decimal(row[3])
                            quotes_count=quotes_count+1
                            self.log.append(quote.save())
                        except:
                            self.log.append("Error parsing date"+ str(row) )
                    else: #It's an hour
                        try:
                            quote=Quotes()
                            quote.products=product
                            quote.datetime=string2dtaware(row[16],"%H:%M:%S", self.request.globals["mem__localzone"])
                            quote.quote=string2decimal(row[3])
                            quotes_count=quotes_count+1
                            self.log.append(quote.save())
                        except:
                            self.log.append("Error parsing hour" + str(row))
            line_count += 1
        lis=""
        for o in self.log:
            lis=lis+f"<li>{o}</li>"
        messages.info(self.request,f"""Managed {quotes_count} quotes from {line_count} CSV lines
    <ul>
        {lis}
    </ul>""")

    ## Imports data from a CSV file with this struct. It has 6 columns
    ## "Fecha","Último","Apertura","Máximo","Mínimo","Vol.","% var."
    ## "22.07.2019","10,074","10,060","10,148","9,987","10,36M","-0,08%"
    def append_from_historical(self):
            with open(self.filename) as csv_file:
                csv_reader = reader(csv_file, delimiter=',')
                line_count = 0
                for row in csv_reader:
                    if line_count >0:#Ignores headers line
                        try:
                            ohcl=OHCLDaily(self.mem)
                            ohcl.product=self.product
                            ohcl.date=string2date(row[0], "DD.MM.YYYY")
                            ohcl.close=string2decimal(row[1])
                            ohcl.open=string2decimal(row[2])
                            ohcl.high=string2decimal(row[3])
                            ohcl.low=string2decimal(row[4])
                            for quote in ohcl.generate_4_quotes():
                                self.append(quote)
                        except:
                            debug("Error parsing" + str(row))
                    line_count += 1
            print("Added {} quotes from {} CSV lines".format(self.length(), line_count))
