from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

EXCLUDED_USER = "marko"
NEW_PASSWORD = "Belgrado_2026"


class Command(BaseCommand):
    help = "Reset all users passwords to the default, except for the admin (marko)"

    def handle(self, *args, **options):
        users = User.objects.exclude(username=EXCLUDED_USER)
        count = 0
        for user in users:
            user.set_password(NEW_PASSWORD)
            user.save()
            self.stdout.write(f"  Updated: {user.username}")
            count += 1

        self.stdout.write(self.style.SUCCESS(f"\nDone. {count} user(s) updated."))
