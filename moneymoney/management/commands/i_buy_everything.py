from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Script to help in I buy all strategy with CFD'

    def handle(self, *args, **options):
        """
            Esta función solicita al usuario que ingrese tres números, calcula su promedio  y muestra el resultado en la consola.
        """

#            primera_capa_alcista = float(input("Ingresa el primer precio de compra: "))
#            alcista = bool(input("Ingresa 1 si es alcista y si no 0"))
#            maximo = float(input("Ingresa el segundo número: "))
#            minimo = float(input("Ingresa el tercer número: "))
            
        
        apalancamiento=20
            
        primera_capa_alcista=20440 
        capas_alcistas=9
        capas_bajistas=8
        
        minimo=primera_capa_alcista-10*capas_bajistas
        maximo=primera_capa_alcista+10*(capas_alcistas-1)
        
        print ("Estudio en dolares)")
        
        print("Capa primera_capa_alcista", primera_capa_alcista,  "US100",  "Capas alcistas",  capas_alcistas,  "Capas bajistas",  capas_bajistas)
        print("Minimo", minimo)
        print("Maximo",  maximo)
                
        for precio_venta in range(primera_capa_alcista,30000, 10):
            ganancia_total=self.ganancia(precio_venta, primera_capa_alcista, precio_venta,  apalancamiento)-self.ganancia(precio_venta, minimo, primera_capa_alcista , apalancamiento)#alcista - bajista
            if ganancia_total>10:
                print("Ganancia total bien en ",  precio_venta,  "=",  ganancia_total,  "$")
                print("Capas desde primera_capa_alcista", self.capas_entre(primera_capa_alcista, precio_venta))
                break

        print()
        print("ESTUDIO MAL")        
        for precio_venta in range(primera_capa_alcista,0, -10):
            ganancia_total=-self.ganancia(precio_venta, primera_capa_alcista, maximo,  apalancamiento)+self.ganancia(precio_venta, precio_venta, primera_capa_alcista-10 , apalancamiento)#alcista - bajista .-10 porque empieza en alcista
            if ganancia_total>10:
                print("Ganancia total malen ",  precio_venta,  "=",  ganancia_total,  "$")
                print("Capas desde primera_capa_alcista", self.capas_entre(primera_capa_alcista, precio_venta))
                break


    def capas_entre(self, a,  b):
        return int(abs(a-b)/10)
        
        
    def ganancia(self,  precio,  capa_baja,  capa_alta, apalancamiento):
        r=0
        for capa in range(capa_baja,  capa_alta+10,  10):
            r+=abs(precio-capa)*0.01*apalancamiento
#        print("Ganancia en ", precio,  capa_baja,  capa_alta,  "es",   r)
        return r
        

