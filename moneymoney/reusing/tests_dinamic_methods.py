import importlib
import glob
from types import MethodType
from os import getcwd,chdir
from sys import path

# def add_methodtypes_to_this_object_dinamically(class_, files_pattern, use_class_name=False):

#     """
#         Usado para añadir metodos al inicial un objeto directamente de otros ficheros
#     Docstring for add_methodtypes_to_this_object_dinamically
    
#     :param class_: Description
#     :param files_pattern: Description
#     :param use_class_name: Description
#     """
#     lista_ficheros = glob.glob(files_pattern)

#     modules={}
#     for fichero in lista_ficheros:
#         module_string=fichero.replace(".py", "")
#         print(f"Encontrado: {fichero}")
#         modules[module_string]=get_module(module_string)

#     for modules_string, d in modules.items():
#         for f in d["funciones"]:
#             setattr(class_, modules_string+"_"+f, MethodType(getattr(d["module"], f), class_))


def add_method_to_this_class_dinamically(class_, directory, files_pattern, class_name_in_names=False):
    """
        Añade metodos de un directio de ficheros, con un patrón y las mete en una clase dinamicamente
    
    :param class_: Description
    :param directory: Description
    :param files_pattern: Description
    :param class_name_in_names: Description
    """

    chdir(directory)
    path.append(directory)
    modules={}
    for fichero in glob.glob(files_pattern):
        module_string=fichero.replace(".py", "")
        # print(f"Encontrado: {fichero}")
        modules[module_string]=get_module(directory, module_string)

    for modules_string, d in modules.items():
        for f in d["funciones"]:
            setattr(class_, f, getattr(d["module"], f))


def get_module(directory, module_string):

    """Lista las funciones públicas (que no empiezan con '_') de un módulo."""

    module=importlib.import_module(f"{directory.replace('/', '.')}.{module_string}")
    funciones_encontradas = []
    
    # Recorre todos los nombres/atributos del módulo
    for nombre in dir(module):
        # 1. Ignorar atributos internos de Python (empiezan y terminan con __)
        if nombre.startswith('__'):
            continue
            
        # 2. Obtener el objeto asociado a ese nombre
        objeto = getattr(module, nombre)
        
        # 3. Verificar si el objeto es una función y no una clase.
        #    Una clase también es "callable", por lo que la filtramos.
        if callable(objeto) and not isinstance(objeto, type):
            # Opcional: Filtramos las funciones que empiezan con '_' (se consideran internas/privadas)
            if not nombre.startswith('_'):
                funciones_encontradas.append(nombre)
    
    return {"module": module, "funciones": funciones_encontradas}

