import os

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from hue_portal.core.models import UserProfile


class Command(BaseCommand):
    help = "Seed default admin and user accounts based on environment variables."

    def handle(self, *args, **options):
        User = get_user_model()

        admin_username = os.environ.get("DEFAULT_ADMIN_USERNAME", "admin")
        admin_email = os.environ.get("DEFAULT_ADMIN_EMAIL", "admin@example.com")
        admin_password = os.environ.get("DEFAULT_ADMIN_PASSWORD", "Admin@123")

        citizen_username = os.environ.get("DEFAULT_USER_USERNAME", "user")
        citizen_email = os.environ.get("DEFAULT_USER_EMAIL", "user@example.com")
        citizen_password = os.environ.get("DEFAULT_USER_PASSWORD", "User@123")

        self._create_user(User, admin_username, admin_email, admin_password, UserProfile.Roles.ADMIN)
        self._create_user(User, citizen_username, citizen_email, citizen_password, UserProfile.Roles.USER)

    def _create_user(self, User, username, email, password, role):
        user, created = User.objects.get_or_create(username=username, defaults={"email": email})
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created user {username}."))
        else:
            if email and user.email != email:
                user.email = email
        if password:
            user.set_password(password)
        user.save()

        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.role = role
        profile.save()

        self.stdout.write(self.style.SUCCESS(f"Ensured role {role} for user {username}."))


