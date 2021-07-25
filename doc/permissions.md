# MyLibrary permissions

## MyLibrary user profiles

This app has the following profiles:

1. Superuser. All permissions and admin site is available to the only system user.

## How to control permissions

To see if a user is autenticated in a template: `{% if user.is_authenticated %}`

To see if a user is staff in a template: `{% if user.is_staff %}`. Function decorator: `staff_member_required`.

To see if a user has a permission in a template: `{% if perms.catalog.can_mark_returned %}`. Function decorator: `@permission_required('catalog.can_mark_returned')`

To see if a user is anonymous in a template: `user.is_anonymous`

## Assign permissions to groups in migrations

There are a few ways around it:

1. Split it into two separate migrations (create permissions and then assign them) and run them with two separate python manage.py migrate commands:

```bash
    python manage.py migrate my_app 0066_create_permissions
    python manage.py migrate my_app 0067_assign_permissions
```

   This allows the post-migrate signal to be emitted after 0066 is run to create the permissions.

2. Split it up into two steps inside one migration, but you'll have to manually create the permissions with a Python function and then assign them in another. You'll have to modify your operations to account for that. One benefit of this is that if want to, you can create a Python function or functions to reverse the migration as well, which isn't really possible for #3 or #4.

3. Emit the post-migrate signal yourself during the migration. This is a good solution for cases where you need permissions from 3rd party apps (like django-guardian, as in my case) so that you can apply them in data migrations.

```python
    from django.apps import apps as django_apps
    def guardian_post_migrate_signal(apps, schema_editor):
        guardian_config = django_apps.get_app_config('guardian')
        models.signals.post_migrate.send(
            sender=guardian_config,
            app_config=guardian_config,
            verbosity=2,
            interactive=False,
            using=schema_editor.connection.alias,
        )
```

4. This is similar to #3, but a little easier. There are probably subtle ways in which it is better or worse, but I'm not sure of what they are. You can create a function which calls django.contrib.auth.management.create_permissions (credit to this post) and use it directly in your migration:

```python
    from django.contrib.auth.management import create_permissions

    def create_perms(apps, schema_editor):
        for app_config in apps.get_app_configs():
            app_config.models_module = True
            create_permissions(app_config, apps=apps, verbosity=0)
            app_config.models_module = None
```

   Then your operations would look like:

```python
        operations = [
            migrations.AlterModelOptions(
                name='my_model',
                options={'permissions': (('my_new_permission_code', 'Permission name'),)},
            ),
            migrations.RunPython(create_perms),
            migrations.RunPython(assign_perms)
        ]
```

