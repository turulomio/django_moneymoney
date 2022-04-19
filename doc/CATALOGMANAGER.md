To be a django_moneymoney catalog manager, you should create in your instance with django admin a permission manually called "catalogmanager" and giving it to the user.

insert into auth_permission (name, content_type_id, codename) values('Allow user to manage catalogs. Only developers', 1, 'catalogmanager');

Look for the id of the authpermission (In my case 137) 

insert into auth_user_user_permissions(user_id, permission_id) values (1, 137);

Now you could edit catalogs from moneymoney

After edition you should call python manager catalogs to export them


