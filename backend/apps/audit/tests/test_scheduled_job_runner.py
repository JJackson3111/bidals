import subprocess
from pathlib import Path


def test_scheduled_job_runner_has_valid_shell_syntax():
    script = Path(__file__).resolve().parents[3] / "scripts" / "run_scheduled_job.sh"

    result = subprocess.run(["sh", "-n", str(script)], capture_output=True, text=True)

    assert result.returncode == 0, result.stderr


def test_scheduled_job_runner_forces_prod_settings_and_database_env():
    script = (Path(__file__).resolve().parents[3] / "scripts" / "run_scheduled_job.sh").read_text()

    assert 'export DJANGO_SETTINGS_MODULE="bidals.settings.prod"' in script
    assert "DJANGO_DATABASE_URL" in script
    assert "DATABASE_URL or DJANGO_DATABASE_URL must be set" in script
    assert "close_expired_auctions|monitor_bid_anomalies|deliver_notifications" in script
