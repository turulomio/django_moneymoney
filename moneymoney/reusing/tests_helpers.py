## THIS IS FILE IS FROM https://github.com/turulomio/django_calories_tracker/calories_tracker/tests_helpers.py
## IF YOU NEED TO UPDATE IT PLEASE MAKE A PULL REQUEST IN THAT PROJECT AND DOWNLOAD FROM IT
## DO NOT UPDATE IT IN YOUR CODE

## It's used to autamatize common test classifing them by FACTORY_TYPES
## You'll have to do your own tests

## Some payloads are generated automatically. For complex payloads, you can pass your own function to autmatize this common tests

## Client must have user attribute in instatntiation

from json import loads
from rest_framework import status

FACTORY_TYPES=        [
            "PublicCatalog", #Catalog can be listed  and retrieved LR without authentication. Nobody can CUD
            "PrivateCatalog", #Catalog can be listed  and retrieved only with authentication. Nobody can CUD
            "PublicEditableCatalog", #Catalog can be listed  and retrieved LR without authentication. CatalogManager group can CUD
            "PrivateEditableCatalog", #Catalog can be listed  and retrieved only with authentication. CatalogManagert group can CUD
            "Private", #Table content  is filtered by authenticated user. User can¡t see other users content
            "Colaborative",  # All authenticated user can LR and CUD
            "Public",  # models can be LR for anonymous users
            "Anonymous",  #Anonymous users can LR and CUD
        ]



def test_cross_user_data(apitestclass, client1,  client2,  url):
    """
        Test to check if a hyperlinked model url can be accesed by client_belongs and not by client_other
        
        example:
        test_cross_user_data(self, client1, client2, "/api/biometrics/2/"})
    """
   
    #other tries to access url
    r=client1.get(url)
    apitestclass.assertEqual(r.status_code, status.HTTP_200_OK,  url)
    
    #other tries to access url
    r=client2.get(url)
    apitestclass.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND, f"{url}. WARNING: Client2 can access Client1 post")


def client_response_to_dict(r):
    """
        Converts client.post response to a dict with content results
    """
    if len(r.content)==0:
        return {}
    return loads(r.content)

def client_post(apitestclass, client, url, params, response_code):
    """
        Makes a client post and returns dictionary with response.content
        Asserts response_code
    """
    r=client.post(url, params, format="json")
    apitestclass.assertEqual(r.status_code,response_code,  f"Error in post {url}, {params} with user {client.user}. {r} {r.content}")
    return client_response_to_dict(r)

def client_get(apitestclass, client, url, response_code):
    """
        Makes a client post and returns dictionary with response.content
        Asserts response_code
    """
    r=client.get(url, format="json")
    apitestclass.assertEqual( r.status_code, response_code,  f"Error in  get {url}  with user {client.user}. {r} {r.content}")
    return client_response_to_dict(r)


#Hyperlinkurl
def hlu(url, id):
    return f'http://testserver{url}{id}/'


def common_actions_tests(apitestclass,  client, post_url, post_payload, failback_id, post=status.HTTP_200_OK, get=status.HTTP_200_OK, list=status.HTTP_200_OK,  put=status.HTTP_200_OK, patch=status.HTTP_200_OK, delete=status.HTTP_200_OK):
    """
        Function to test all request types after one post
        
        failback_id. If first post fails, I need and id to keep testing
    """
    created_json=client_post(apitestclass, client, post_url, post_payload, post)
    try:
        id=created_json["id"]
    except:#User couldn't post any, I look for a id in database  to check the rest of actions, son in automatic test make a first post
        id=failback_id

    hlu_id=hlu(post_url,id)

    r=client.get(post_url)
    apitestclass.assertEqual(r.status_code, list, f"list method of {post_url}")
    r=client.get(hlu_id)
    apitestclass.assertEqual(r.status_code, get, f"retrieve method of {hlu_id}")
    r=client.put(hlu_id, created_json,format="json")
    apitestclass.assertEqual(r.status_code, put, f"update method of {hlu_id}")
    r=client.patch(hlu_id, created_json,format="json")
    apitestclass.assertEqual(r.status_code, patch, f"partial_update method of {hlu_id}")
    r=client.delete(hlu_id)
    apitestclass.assertEqual(r.status_code, delete, f"destroy method of {hlu_id}")

def common_tests_PrivateCatalog(apitestclass,  post_url, post_payload, fallback_id,  client_authenticated_1, client_anonymous, client_catalog_manager):
    """
        Function make all checks to privatecatalogs with different clients
        A private catalogs is a table that can't be CUD by nobody, but can be RL by authenticated users
        This kind of table is created by loaddata or fixtures
    """    
    ### TEST OF CLIENT_AUTHENTICATED_1
    common_actions_tests(apitestclass, client_authenticated_1, post_url, post_payload, fallback_id, 
        post=status.HTTP_403_FORBIDDEN, 
        get=status.HTTP_200_OK, 
        list=status.HTTP_200_OK, 
        put=status.HTTP_403_FORBIDDEN, 
        patch=status.HTTP_403_FORBIDDEN, 
        delete=status.HTTP_403_FORBIDDEN
    )            
    ### TEST OF CLIENT_ANONYMOUS
    common_actions_tests(apitestclass, client_anonymous, post_url, post_payload, fallback_id, 
        post=status.HTTP_401_UNAUTHORIZED, 
        get=status.HTTP_401_UNAUTHORIZED, 
        list=status.HTTP_401_UNAUTHORIZED, 
        put=status.HTTP_401_UNAUTHORIZED, 
        patch=status.HTTP_401_UNAUTHORIZED, 
        delete=status.HTTP_401_UNAUTHORIZED
    )    
    ### TEST OF CLIENT_CATALOG_MANAGER
    common_actions_tests(apitestclass, client_catalog_manager, post_url, post_payload, fallback_id, 
        post=status.HTTP_201_CREATED, 
        get=status.HTTP_200_OK, 
        list=status.HTTP_200_OK, 
        put=status.HTTP_200_OK, 
        patch=status.HTTP_200_OK, 
        delete=status.HTTP_204_NO_CONTENT
    )

def common_tests_PrivateEditableCatalog(apitestclass,  post_url, post_payload, client_authenticated_1, client_anonymous, client_catalog_manager):
    """
        Function make all checks to privatecatalogs factories with different clients
        A private catalogs is for example SystemProducts, only can be CUD by client_catalog_manager
    """    
    ### ALWAYS ONE REGISTER TO TEST FALBACK ID
    dict_post=client_post(apitestclass, client_catalog_manager, post_url, post_payload, status.HTTP_201_CREATED)
    ### TEST OF CLIENT_AUTHENTICATED_1
    common_actions_tests(apitestclass, client_authenticated_1, post_url, post_payload, dict_post["id"], 
        post=status.HTTP_403_FORBIDDEN, 
        get=status.HTTP_200_OK, 
        list=status.HTTP_200_OK, 
        put=status.HTTP_403_FORBIDDEN, 
        patch=status.HTTP_403_FORBIDDEN, 
        delete=status.HTTP_403_FORBIDDEN
    )            
    ### TEST OF CLIENT_ANONYMOUS
    common_actions_tests(apitestclass, client_anonymous, post_url, post_payload, dict_post["id"], 
        post=status.HTTP_401_UNAUTHORIZED, 
        get=status.HTTP_401_UNAUTHORIZED, 
        list=status.HTTP_401_UNAUTHORIZED, 
        put=status.HTTP_401_UNAUTHORIZED, 
        patch=status.HTTP_401_UNAUTHORIZED, 
        delete=status.HTTP_401_UNAUTHORIZED
    )    
    ### TEST OF CLIENT_CATALOG_MANAGER
    common_actions_tests(apitestclass, client_catalog_manager, post_url, post_payload, dict_post["id"], 
        post=status.HTTP_201_CREATED, 
        get=status.HTTP_200_OK, 
        list=status.HTTP_200_OK, 
        put=status.HTTP_200_OK, 
        patch=status.HTTP_200_OK, 
        delete=status.HTTP_204_NO_CONTENT
    )


def common_tests_Collaborative(apitestclass, post_url, post_payload, client_authenticated_1, client_authenticated_2, client_anonymous):
    """
    Function Makes all action operations to factory with client to all examples

    """
    ### ALWAYS ONE REGISTER TO TEST FALBACK ID
    dict_post=client_post(apitestclass, client_authenticated_1, post_url, post_payload, status.HTTP_201_CREATED)
    
    ### TEST OF CLIENT_AUTHENTICATED_1
    common_actions_tests(apitestclass, client_authenticated_1, post_url, post_payload, dict_post["id"], 
        post=status.HTTP_201_CREATED, 
        get=status.HTTP_200_OK, 
        list=status.HTTP_200_OK, 
        put=status.HTTP_200_OK, 
        patch=status.HTTP_200_OK, 
        delete=status.HTTP_204_NO_CONTENT
    )         
    
    ### TEST OF CLIENT_AUTHENTICATED_2
    common_actions_tests(apitestclass, client_authenticated_2, post_url, post_payload, dict_post["id"], 
        post=status.HTTP_201_CREATED, 
        get=status.HTTP_200_OK, 
        list=status.HTTP_200_OK, 
        put=status.HTTP_200_OK, 
        patch=status.HTTP_200_OK, 
        delete=status.HTTP_204_NO_CONTENT
    )
    
    ### TEST OF CLIENT_ANONYMOUS
    common_actions_tests(apitestclass, client_anonymous, post_url, post_payload, dict_post["id"], 
        post=status.HTTP_401_UNAUTHORIZED, 
        get=status.HTTP_401_UNAUTHORIZED, 
        list=status.HTTP_401_UNAUTHORIZED, 
        put=status.HTTP_401_UNAUTHORIZED, 
        patch=status.HTTP_401_UNAUTHORIZED, 
        delete=status.HTTP_401_UNAUTHORIZED
    )     
    
def common_tests_Private(apitestclass,  post_url, post_payload, client_authenticated_1, client_authenticated_2, client_anonymous):
    """
       Make Private model tests
       Data that can only be viewed by own user
    """
    ### ALWAYS ONE REGISTER TO TEST FALBACK ID
    dict_post=client_post(apitestclass, client_authenticated_1, post_url, post_payload, status.HTTP_201_CREATED)
    
    ### TEST OF CLIENT_AUTHENTICATED_1
    common_actions_tests(apitestclass, client_authenticated_1, post_url, post_payload, dict_post["id"], 
        post=status.HTTP_201_CREATED, 
        get=status.HTTP_200_OK, 
        list=status.HTTP_200_OK, 
        put=status.HTTP_200_OK, 
        patch=status.HTTP_200_OK, 
        delete=status.HTTP_204_NO_CONTENT
    )



    # 1 creates and 2 cant get
    r1=client_authenticated_1.post(post_url, post_payload, format="json")
    apitestclass.assertEqual(r1.status_code, status.HTTP_201_CREATED, f"{post_url}, {r1.content}")
    r1_id=loads(r1.content)["id"]

    hlu_id_r1=hlu(post_url,r1_id)
    
    r=client_authenticated_2.get(hlu_id_r1)
    apitestclass.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND, f"{post_url}, {r.content}. Client2 can access Client1 post")

    ### TEST OF CLIENT_ANONYMOUS
    common_actions_tests(apitestclass, client_anonymous, post_url, post_payload, dict_post["id"], 
        post=status.HTTP_401_UNAUTHORIZED, 
        get=status.HTTP_401_UNAUTHORIZED, 
        list=status.HTTP_401_UNAUTHORIZED, 
        put=status.HTTP_401_UNAUTHORIZED, 
        patch=status.HTTP_401_UNAUTHORIZED, 
        delete=status.HTTP_401_UNAUTHORIZED
    )     
