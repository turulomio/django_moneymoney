from django.core.management.base import BaseCommand
from django.contrib.auth.models import Permission, User


class Command(BaseCommand):
    help = 'Get a list of all permissions available in the system.'

    def add_arguments(self, parser):
        parser.add_argument('--user',  default=None, required=False)
        
    def handle(self, *args, **options):
        permissions = set()

        # We create (but not persist) a temporary superuser and use it to game the
        # system and pull all permissions easily.
        if options['user'] is None:
#            tmp_user = get_user_model()(
#              is_active=True,
#              is_superuser=True
#            )
            # We go over each AUTHENTICATION_BACKEND and try to fetch
            # a list of permissions
#            for backend in auth.get_backends():
#              if hasattr(backend, "get_all_permissions"):
#                permissions.update(backend.get_all_permissions(tmp_user))
            for tmp_user in User.objects.all():
                if tmp_user.is_superuser:
#                    print(tmp_user.get_all_permissions())
#                    permissions.update(tmp_user.user_permissions.all() )
                    break
        else:
            tmp_user = User.objects.get(username=options['user'])
#            permissions.update(tmp_user.user_permissions.all() | Permission.objects.filter(group__user=tmp_user))
#            permissions.update(tmp_user.user_permissions.all() | Permission.objects.filter(group__user=tmp_user))
#            print(tmp_user.get_all_permissions())
            # Make an unique list of permissions sorted by permission name.
#            sorted_list_of_permissions = sorted(list(permissions),  key=lambda item: item.codename)
        
        
        permissions=sorted(tmp_user.get_all_permissions())
        for permission_string in permissions :
            app_label,  codename = permission_string.split(".")
            p=Permission.objects.get(content_type__app_label=app_label, codename=codename)
            print ("{} ==> {}".format(permission_string, p.name))

