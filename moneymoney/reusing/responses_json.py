## THIS IS FILE IS FROM https://github.com/turulomio/reusingcode/python/responses_json.py
## IF YOU NEED TO UPDATE IT PLEASE MAKE A PULL REQUEST IN THAT PROJECT AND DOWNLOAD FROM IT
## DO NOT UPDATE IT IN YOUR CODE

from django.http import JsonResponse
from .myjsonencoder import MyJSONEncoder

def json_success_response(success, detail_):
    """
        Returns a predefined json response
            - success: bool
            - detail: Description of success
    """
    if not success.__class__.__name__=="bool" or not detail_.__class__.__name__ in ("str", "__proxy__"):
        print("json_succcess_response parameters are wrong")

    return JsonResponse( {"success": success, "detail": detail_}, encoder=MyJSONEncoder, safe=True)

def json_data_response(success, data,  detail=""):
    """
        Returns a predefined json response
            - success: bool
            - data: Dict
            - detail: Description of success
    """
    if not success.__class__.__name__=="bool"  or not detail.__class__.__name__ in ("str", "__proxy__") or not data.__class__.__name__ in ["dict", "OrderedDict", "list"]:
        print("json_data_response parameters are wrong")
        
    return JsonResponse( {"success": success,  "data": data,  "detail": detail}, encoder=MyJSONEncoder, safe=True)
