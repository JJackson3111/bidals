from django.core.management.base import BaseCommand

from apps.audit.services.staging_diagnostics import collect_deployment_fingerprint


class Command(BaseCommand):
    help = "Print safe BIDALS deployment fingerprint information without exposing secrets."

    def handle(self, *args, **options):
        self.stdout.write("deployment_fingerprint")
        for line in collect_deployment_fingerprint():
            self.stdout.write(f"{line.name}={line.value}")
