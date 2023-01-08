from rest_framework import permissions

class GroupCatalogManager(permissions.BasePermission):
    """Permiso que comprueba si pertenece al grupo Interventor """
    def has_permission(self, request, view):
        return request.user.groups.filter(name="CatalogManager").exists()
    

