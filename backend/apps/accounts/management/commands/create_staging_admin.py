import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q

from apps.accounts.models import UserRole
from apps.audit.models import AuditAction, AuditLog
from apps.audit.services.readiness import runtime_environment


DEFAULT_PASSWORD_ENV = "STAGING_ADMIN_PASSWORD"


class Command(BaseCommand):
    help = "Create or update a staging-only BIDALS admin account from environment-provided credentials."

    def add_arguments(self, parser):
        parser.add_argument("--username", default="staging_admin", help="Username for the staging admin account.")
        parser.add_argument("--email", default="admin@bidals.staging.test", help="Email for the staging admin account.")
        parser.add_argument(
            "--password-env",
            default=DEFAULT_PASSWORD_ENV,
            help="Environment variable containing the admin password.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Allow running outside BIDALS_ENV=staging. Required for any non-staging environment.",
        )

    def handle(self, *args, **options):
        environment = runtime_environment()
        if environment != "staging" and not options["force"]:
            raise CommandError("Refusing to create staging admin outside BIDALS_ENV=staging without --force.")

        username = options["username"].strip()
        email = options["email"].strip().lower()
        password_env = options["password_env"].strip()
        password = os.getenv(password_env, "")

        if not username:
            raise CommandError("Username is required.")
        if not email:
            raise CommandError("Email is required.")
        if not password:
            raise CommandError(f"{password_env} must be set in the environment. The password is never read from code.")
        if len(password) < 12:
            raise CommandError(f"{password_env} must be at least 12 characters long.")

        User = get_user_model()
        with transaction.atomic():
            matches = list(User.objects.filter(Q(email=email) | Q(username=username)).order_by("id"))
            if len({user.id for user in matches}) > 1:
                raise CommandError("Username and email belong to different existing users; resolve this manually.")

            user = matches[0] if matches else None
            created = user is None
            if user is None:
                user = User(email=email)

            user.username = username
            user.email = email
            user.role = UserRole.ADMIN
            user.is_staff = True
            user.is_superuser = True
            user.is_active = True
            user.set_password(password)
            user.save()

            AuditLog.objects.create(
                actor=None,
                action=AuditAction.ADMIN_ACTION,
                entity_type="staging_admin",
                entity_id=str(user.id),
                metadata={
                    "environment": environment,
                    "created": created,
                    "username": user.username,
                    "email": user.email,
                    "role": user.role,
                    "is_staff": user.is_staff,
                    "is_superuser": user.is_superuser,
                    "forced": bool(options["force"]),
                    "password_env": password_env,
                },
            )

        action = "created" if created else "updated"
        self.stdout.write(self.style.SUCCESS(f"Staging admin {action}: {user.username} ({user.email})"))
        self.stdout.write("Password was read from environment and was not printed.")
