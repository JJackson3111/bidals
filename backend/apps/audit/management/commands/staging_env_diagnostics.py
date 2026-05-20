from django.core.management.base import BaseCommand

from apps.audit.services.staging_diagnostics import collect_staging_env_diagnostics


class Command(BaseCommand):
    help = "Print safe BIDALS staging environment diagnostics without exposing secrets."

    def handle(self, *args, **options):
        self.stdout.write("staging_env_diagnostics")
        for line in collect_staging_env_diagnostics():
            self.stdout.write(f"{line.name}={line.value}")
