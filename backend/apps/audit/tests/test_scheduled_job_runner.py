import subprocess
from pathlib import Path


def test_scheduled_job_runner_has_valid_shell_syntax():
    script = Path(__file__).resolve().parents[3] / "scripts" / "run_scheduled_job.sh"

    result = subprocess.run(["sh", "-n", str(script)], capture_output=True, text=True)

    assert result.returncode == 0, result.stderr


def test_scheduled_job_runner_validates_prod_settings_and_database_env():
    script = (Path(__file__).resolve().parents[3] / "scripts" / "run_scheduled_job.sh").read_text()

    assert "DJANGO_SETTINGS_MODULE must be bidals.settings.prod" in script
    assert "DJANGO_SECRET_KEY" in script
    assert "DJANGO_ALLOWED_HOSTS" in script
    assert "DJANGO_DATABASE_URL" in script
    assert "DATABASE_URL_or_DJANGO_DATABASE_URL" in script
    assert "scheduled job is missing required production env vars" in script
    assert "Secret values were not printed" in script
    assert "redis_env=pass" in script
    assert "s3_env=pass" in script
    assert "email_env=pass" in script
    assert "dirname" not in script
    assert "${0%/*}" in script
    assert "close_expired_auctions|monitor_bid_anomalies|deliver_notifications" in script


def test_production_dockerfile_exposes_scheduled_job_runner():
    dockerfile = (Path(__file__).resolve().parents[3] / "Dockerfile").read_text()

    assert "test -f /app/scripts/run_scheduled_job.sh" in dockerfile
    assert "chmod +x /app/scripts/run_scheduled_job.sh" in dockerfile
    assert "ln -sf /app/scripts/run_scheduled_job.sh /usr/local/bin/bidals-scheduled-job" in dockerfile
