import csv
from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.accounts.models import UserRole
from apps.audit.models import AuditAction, AuditLog

pytestmark = pytest.mark.django_db

User = get_user_model()


def create_user(username, role=UserRole.BIDDER):
    return User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="StrongPass123!",
        role=role,
    )


def authenticated_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def test_admin_can_export_activity_with_filters_and_audit_log():
    admin = create_user("admin", role=UserRole.ADMIN)
    AuditLog.objects.create(
        actor=admin,
        action=AuditAction.OUTCOME_REPAIR_APPROVED,
        entity_type="outcome_repair",
        entity_id="7",
        metadata={"repair_id": 7, "request_id": "req-1", "secret_token": "do-not-export"},
    )
    AuditLog.objects.create(
        actor=admin,
        action=AuditAction.BID_ACCEPTED,
        entity_type="lot",
        entity_id="3",
        metadata={"lot_id": 3},
    )
    client = authenticated_client(admin)

    response = client.get("/api/admin/activity/export/?action_type=outcome_repair_approved")

    assert response.status_code == 200
    assert response["Content-Type"] == "text/csv"
    rows = list(csv.DictReader(StringIO(response.content.decode())))
    assert [row["action"] for row in rows] == [AuditAction.OUTCOME_REPAIR_APPROVED]
    assert rows[0]["admin_username"] == "admin"
    assert rows[0]["request_id"] == "req-1"
    assert "do-not-export" not in rows[0]["metadata_summary"]
    assert "[REDACTED]" in rows[0]["metadata_summary"]
    assert AuditLog.objects.filter(action=AuditAction.ADMIN_ACTIVITY_EXPORTED, actor=admin).exists()


def test_non_admin_cannot_export_activity():
    seller = create_user("seller", role=UserRole.SELLER)
    bidder = create_user("bidder", role=UserRole.BIDDER)

    assert authenticated_client(seller).get("/api/admin/activity/export/").status_code == 403
    assert authenticated_client(bidder).get("/api/admin/activity/export/").status_code == 403
