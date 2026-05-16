from apps.audit.management.commands.verify_backup import Command as VerifyBackupCommand


class Command(VerifyBackupCommand):
    help = "Alias for verify_backup; verifies BIDALS backup readiness without destructive restore actions."
