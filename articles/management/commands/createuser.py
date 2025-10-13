from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = "Create a new user (regular or admin)"

    def add_arguments(self, parser):
        parser.add_argument("username", type=str, help="Username for the new user")
        parser.add_argument("password", type=str, help="Password for the new user")
        parser.add_argument(
            "--admin",
            action="store_true",
            help="Create user as admin/staff",
        )
        parser.add_argument(
            "--email",
            type=str,
            default="",
            help="Email for the new user",
        )

    def handle(self, *args, **options):
        username = options["username"]
        password = options["password"]
        email = options["email"]
        is_admin = options["admin"]

        # Check if user already exists
        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.ERROR(f'❌ User "{username}" already exists'))
            return

        # Create the user
        if is_admin:
            user = User.objects.create_superuser(
                username=username, password=password, email=email
            )
            self.stdout.write(
                self.style.SUCCESS(f'✅ Admin user "{username}" created successfully')
            )
        else:
            user = User.objects.create_user(
                username=username, password=password, email=email
            )
            self.stdout.write(
                self.style.SUCCESS(f'✅ Regular user "{username}" created successfully')
            )

        self.stdout.write(f"   Username: {username}")
        self.stdout.write(f"   Email: {email or 'Not provided'}")
        self.stdout.write(f"   Is Admin: {is_admin}")
