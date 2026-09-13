from django.db import migrations
from django.contrib.auth.hashers import make_password


def setup_existing_users(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    for user in User.objects.all():
        changed = False

        # Assign a username if missing
        if not user.username:
            base = user.email.split('@')[0] if user.email else f"user{user.pk}"
            username = base
            counter = 1
            while User.objects.filter(username=username).exclude(pk=user.pk).exists():
                counter += 1
                username = f"{base}{counter}"
            user.username = username
            changed = True

        # Reset password and force change on first login
        user.password = make_password('Welcome@123')
        user.must_change_password = True
        changed = True

        if changed:
            user.save()


def reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(setup_existing_users, reverse),
    ]