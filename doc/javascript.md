# Django Money information
https://docs.npmjs.com/creating-a-package-json-file
## Structure

Django money is designed to run a user in a database

If you need several users you need to install several apps with different settings

Xulpymoney is not going to be replaced until the project was succesful. At this moment I'll valorate the result to start managing schema from django and to stop Xulpymoney development

It's necessary to change xulpymoney schema to a modern and english one. After that replace models with python manage.py inspectdb > money/model.py. Perhaps you need to rename admin.py temporary

## Users

Each database will have only one user, created in installation

* root. Created in installation

## Admin page

Admin page only will be showed if it's set in settings

Users and groups won't be visible in admin

## Migrations

Only there will be a migration to install django settings in database (Harmless). Models will not manage schema