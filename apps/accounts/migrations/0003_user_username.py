from django.db import migrations, models


def populate_usernames(apps, schema_editor):
    """Set username = email prefix for all existing users."""
    User = apps.get_model("accounts", "User")
    seen = set()
    for user in User.objects.all():
        base = user.email.split("@")[0].lower()
        username = base
        counter = 1
        while username in seen or User.objects.filter(username=username).exists():
            username = f"{base}{counter}"
            counter += 1
        seen.add(username)
        user.username = username
        user.save(update_fields=["username"])


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_team_teammembership_user_otp_enabled_and_more"),  # adjust to your last migration
    ]

    operations = [
        # Step 1: add column without unique, allow blank
        migrations.AddField(
            model_name="user",
            name="username",
            field=models.CharField(max_length=150, blank=True, default=""),
            preserve_default=False,
        ),
        # Step 2: populate existing rows
        migrations.RunPython(populate_usernames, migrations.RunPython.noop),
        # Step 3: now apply unique constraint
        migrations.AlterField(
            model_name="user",
            name="username",
            field=models.CharField(max_length=150, unique=True),
        ),
    ]