import pytest
from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APIClient

from apps.leads.models import LeadRequest, LeadSourcePage, LeadStatus

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def clear_lead_rate_cache():
    cache.clear()
    yield
    cache.clear()


def lead_payload(**overrides):
    payload = {
        "name": "Avery Brooks",
        "email": "AVERY@example.org",
        "organisation": "North Star Foundation",
        "fundraising_focus": "auctions",
        "message": "We are planning a gala auction for 300 supporters in November.",
        "source_page": LeadSourcePage.BOOK_DEMO,
    }
    payload.update(overrides)
    return payload


def test_valid_lead_submission_succeeds():
    client = APIClient()

    response = client.post("/api/leads/", lead_payload(), format="json")

    lead = LeadRequest.objects.get()
    assert response.status_code == 201
    assert response.data["id"] == lead.id
    assert response.data["status"] == LeadStatus.NEW
    assert lead.email == "avery@example.org"
    assert lead.source_page == LeadSourcePage.BOOK_DEMO


def test_missing_required_fields_fail():
    client = APIClient()

    response = client.post("/api/leads/", lead_payload(name="", organisation="", message=""), format="json")

    assert response.status_code == 400
    assert "name" in response.data
    assert "organisation" in response.data
    assert "message" in response.data
    assert not LeadRequest.objects.exists()


def test_invalid_email_fails():
    client = APIClient()

    response = client.post("/api/leads/", lead_payload(email="not-an-email"), format="json")

    assert response.status_code == 400
    assert "email" in response.data
    assert not LeadRequest.objects.exists()


def test_long_message_rejected():
    client = APIClient()

    response = client.post("/api/leads/", lead_payload(message="x" * 2001), format="json")

    assert response.status_code == 400
    assert "message" in response.data
    assert not LeadRequest.objects.exists()


def test_unauthenticated_public_submission_allowed():
    client = APIClient()

    response = client.post("/api/leads/", lead_payload(source_page=LeadSourcePage.CONTACT), format="json")

    assert response.status_code == 201
    assert LeadRequest.objects.filter(source_page=LeadSourcePage.CONTACT).exists()


@override_settings(RATE_LIMIT_LEAD_REQUESTS="1/hour")
def test_lead_submission_rate_limit_by_ip():
    client = APIClient(REMOTE_ADDR="203.0.113.10")

    first = client.post("/api/leads/", lead_payload(email="first@example.org"), format="json")
    second = client.post("/api/leads/", lead_payload(email="second@example.org"), format="json")

    assert first.status_code == 201
    assert second.status_code == 429
    assert second.data["reason"] == "RATE_LIMITED"
    assert second.data["scope"] == "lead_request_ip"
    assert LeadRequest.objects.count() == 1


def test_honeypot_field_rejected_without_storing_lead():
    client = APIClient()

    response = client.post("/api/leads/", lead_payload(website="https://spam.example"), format="json")

    assert response.status_code == 400
    assert response.data["detail"][0] == "Unable to accept this request."
    assert not LeadRequest.objects.exists()
