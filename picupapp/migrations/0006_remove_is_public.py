from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('picupapp', '0012_auto_xyz'),  # Replace with your actual latest migration name (no .py)
    ]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE picupapp_photoupload DROP COLUMN IF EXISTS is_public;",
            reverse_sql="ALTER TABLE picupapp_photoupload ADD COLUMN is_public BOOLEAN;"
        )
    ]
