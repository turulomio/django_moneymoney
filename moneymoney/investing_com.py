from datetime import datetime
from django.utils.translation import gettext_lazy as _
from moneymoney.models import Products,  Quotes
from moneymoney import types
from csv import reader
from datetime import timedelta
from io import StringIO
from pydicts import casts

class OHCLDaily:
    def __init__(self, product, date_, open, high, close, low):
        self.product=product
        self.date=date_
        self.open=open
        self.high=high
        self.close=close
        self.low=low

    ## Generate quotes and save them in database
    ## Returns a list of dictionaries with the result
    def generate_4_quotes(self):
        quotes=[]
        
        
        datestart=self.product.stockmarkets.dtaware_starts(self.date)
        dateends=self.product.stockmarkets.dtaware_closes(self.date)
        datetimefirst=datestart-timedelta(seconds=1)
        datetimelow=(datestart+(dateends-datestart)*1/3)
        datetimehigh=(datestart+(dateends-datestart)*2/3)
        datetimelast=dateends+timedelta(microseconds=4)

        quote=Quotes(products=self.product, datetime=datetimefirst, quote=self.open)
        quotes.append({"product": self.product.fullName(),   "code":self.product.ticker_investingcom, "log":quote.save()})
        

        quote=Quotes(products=self.product, datetime=datetimehigh, quote=self.high)
        quotes.append({"product": self.product.fullName(),   "code":self.product.ticker_investingcom, "log":quote.save()})
        

        quote=Quotes(products=self.product, datetime=datetimelast, quote=self.close)
        quotes.append({"product": self.product.fullName(),   "code":self.product.ticker_investingcom, "log":quote.save()})
        

        quote=Quotes(products=self.product, datetime=datetimelow, quote=self.low)
        quotes.append({"product": self.product.fullName(),   "code":self.product.ticker_investingcom, "log":quote.save()})
        return quotes
        

class InvestingCom:
    def __init__(self, timezone_name):
        self.timezone_name=timezone_name
        self.product=None
        self.log=[]
        self.lol=[]#List of list with the info obtained from memory, disk ...
        
    @classmethod
    def from_filename_in_memory(cls, timezone_name, filename_in_memory):
        """
            Crea un investingCom leyendo en memoria un lol y cargandolo
            Una vez cargado se generan las quotes con get()
        """
        r=cls(timezone_name)
        filename_in_memory.seek(0)
        csv_object=reader(StringIO(filename_in_memory.read().decode('utf-8')))
        for row in csv_object:
            r.lol.append(row)
        return r

    @classmethod
    def from_filename_in_disk(cls, timezone_name, filename_in_disk):
        r=cls(timezone_name)
        csv_object=reader(open(filename_in_disk, mode="r", encoding="utf-8"))
        for row in csv_object:
            r.lol.append(row)
        r.lol.pop(0) #Removes first symbol#market
        return r

    @classmethod
    def from_bytes(cls, timezone_name, bytes_):
        r=cls(timezone_name)
        csv_object=reader(StringIO(bytes_.decode("UTF-8")))
        for row in csv_object:
            r.lol.append(row)
        return r

    @classmethod
    def from_lol(cls, timezone_name, lol):
        r=cls(timezone_name)
        r.lol=lol
        return r
        
    def get(self):
        if len(self.lol)==0:
            return
        columns=len(self.lol[0])
        if self.product==None: #Several products
            if columns==8:
                return self.append_from_default()
            elif columns==39:
                self.log.append(_("Adding quotes from Investing.com portfolio"))
                return self.append_from_portfolio()
            else:
                return "NUMBER OF COLUMNS DOESN'T MATCH"
        else:
            return self.append_from_historical()
        
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
#                                date_=casts.str2date(row[7], "DD/MM")
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
        quotes_count = 0
        for row in self.lol:
            if row[2]=="":
                products=Products.objects.filter(ticker_investingcom=row[1]).select_related("stockmarkets")
                code=f"{row[1]}"
            else:
                products=Products.objects.filter(ticker_investingcom=f"{row[1]}#{row[2]}").select_related("stockmarkets")
                code=f"{row[1]}#{row[2]}"

            if len(products)==0:
                r.append({"product":None,   "code":code,  "log": "Product wasn't found"})

            for product in products:
                d={"product": product.fullName(),   "code":code}
                if row[16].find(":")==-1:#It's a date
                    try:
                        quote=Quotes()
                        quote.products=product
                        date_=casts.str2date(row[16], "DD/MM")
                        quote.datetime=casts.dtaware(date_, product.stockmarkets.closes, product.stockmarkets.zone)#Without 4 microseconds becaouse is not a ohcl
                        row[3]=row[3].replace(".", "")#Remove thousand separator                        
                        row[3]=row[3].replace(",", ".")#Change decimal separator to point
                        quote.quote=casts.str2decimal(row[3])

                        quotes_count=quotes_count+1
                        d["log"]=quote.save()
                    except:
                        d["log"]="Error parsing date"+ str(row)
                else: #It's an hour
                    try:
                        quote=Quotes()
                        quote.products=product
                        dtnaive=casts.str2dtnaive(row[16],"%H:%M:%S")
                        quote.datetime=casts.dtaware(dtnaive.date(), dtnaive.time(), self.timezone_name)     
                        row[3]=row[3].replace(".", "")#Remove thousand separator                        
                        row[3]=row[3].replace(",", ".")#Change decimal separator to point
                        quote.quote=casts.str2decimal(row[3])
                        quotes_count=quotes_count+1
                        d["log"]=quote.save()
                    except:
                        d["log"]="Error parsing hour" + str(row)
                r.append(d)
        return r

    ## Imports data from a CSV file with this struct. It has 6 columns
    ## "Fecha","Último","Apertura","Máximo","Mínimo","Vol.","% var."
    ## "22.07.2019","10,074","10,060","10,148","9,987","10,36M","-0,08%"
    def append_from_historical(self):
        r=[]
        line_count = 0
        for row in self.csv_object:
            if line_count >0:#Ignores headers line
#                try:
                for i in range(1, 5):
                    row[i]=row[i].replace(".", "")#Remove thousand separator                        
                    row[i]=row[i].replace(",", ".")#Change decimal separator to point
                ohcl=OHCLDaily(
                    self.product, 
                    casts.str2date(row[0], "DD.MM.YYYY"), 
                    casts.str2decimal(row[2]), 
                    casts.str2decimal(row[3]), 
                    casts.str2decimal(row[1]), 
                    casts.str2decimal(row[4])
                )
                r=r+ohcl.generate_4_quotes()
#                except:
#                    print("Error parsing" + str(row))
            line_count += 1
        print("Added {} quotes from {} CSV lines".format(len(r), line_count))
        return r

    ## Imports data from a CSV file with this struct. It has 6 columns
    ## "Fecha","Último","Apertura","Máximo","Mínimo","Vol.","% var."
    ## "May 23, 2023","10,074","10,060","10,148","9,987","10,36M","-0,08%"
    def append_from_historical_rare_date(self):
        r=[]
        line_count = 0
        for row in self.csv_object:
            if self.product.productstypes.id==types.eProductType.Fund:
                date_=datetime.strptime(row[0], "%b %d, %Y")
                dateends=self.product.stockmarkets.dtaware_closes(date_)
                quote_=casts.str2decimal(row[2].replace(",", "#").replace(".",",").replace("#",""), decimal_separator=",")

                quote=Quotes(products=self.product, datetime=dateends, quote=quote_)
                r.append({"product": self.product.fullName(),   "code":self.product.ticker_investingcom, "log":quote.save()})
        

            else:
                if line_count >0:#Ignores headers line
    #                try:
                    for i in range(1, 5):
                        row[i]=row[i].replace(".", "")#Remove thousand separator                        
                        row[i]=row[i].replace(",", ".")#Change decimal separator to point
                    ohcl=OHCLDaily(
                        self.product, 
                        casts.str2date(row[0], "DD.MM.YYYY"), 
                        casts.str2decimal(row[2]), 
                        casts.str2decimal(row[3]), 
                        casts.str2decimal(row[1]), 
                        casts.str2decimal(row[4])

                    )
                    r=r+ohcl.generate_4_quotes()
    #                except:
    #                    print("Error parsing" + str(row))
            line_count += 1
        print("Added {} quotes from {} CSV lines".format(len(r), line_count))
        return r

    
