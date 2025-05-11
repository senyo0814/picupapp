# picupapp/migrations/000X_remove_is_public.py
from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('picupapp', 'last_migration_name'),  # Replace with your last migration file name (without .py)
    ]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE picupapp_photoupload DROP COLUMN IF EXISTS is_public;",
            reverse_sql="ALTER TABLE picupapp_photoupload ADD COLUMN is_public BOOLEAN;"
        )
    ]
