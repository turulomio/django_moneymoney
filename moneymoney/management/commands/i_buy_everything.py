from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Script to help in I buy all strategy with CFD'

    def handle(self, *args, **options):
        """
            Esta función solicita al usuario que ingrese tres números, calcula su promedio  y muestra el resultado en la consola.
        """

#            inicio = float(input("Ingresa el primer precio de compra: "))
#            alcista = bool(input("Ingresa 1 si es alcista y si no 0"))
#            maximo = float(input("Ingresa el segundo número: "))
#            minimo = float(input("Ingresa el tercer número: "))
            
        
        apalancamiento=20
            
        inicio=20440 
        alcista=True
        capas_mal=5
        
        minimo=inicio-10*capas_mal
        
        
        minimo=20360

        print("Capa inicio", inicio, "Alcista" if alcista else "Bajista", "US100")
#        print("Capas por arriba", (maximo-inicio)/10, "hasta", maximo)
        print("Capas por debajo", (inicio-minimo)/10, "hasta", minimo)

        acciones=(20520-20360)/10/100+0.01
        
        
        print("Acciones totales invertidas", acciones)
        
        invertido=0
#        for capa in range (minimo, maximo+10, 10):
#            print(capa)
        
#            invertido+= 0.01*apalancamiento*capa
        
#        print("Importe invertido", invertido)
        
        capa=20360
        gananciatotal=0
        precio_actual_alcista=inicio
        for precio_actual in range(inicio,30000, 10):
             gananciatotal+=(precio_actual_alcista-capa)*0.01*apalancamiento
#                 for capa in range (minimo, maximo+10, 10):
                    
        
            capa+=10
            precio_actual_alcista+=10
            
    def ganancia_bajista(minimo, precio): 
        

