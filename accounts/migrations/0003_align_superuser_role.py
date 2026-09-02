from django.db import migrations


def align_superuser_roles(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    User.objects.filter(is_superuser=True).update(role='ADMIN', is_staff=True)


class Migration(migrations.Migration):
    dependencies = [('accounts', '0002_user_created_by_user_must_change_password_and_more')]
    operations = [migrations.RunPython(align_superuser_roles, migrations.RunPython.noop)]
