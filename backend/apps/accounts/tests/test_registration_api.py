import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.accounts.models import UserRole

pytestmark = pytest.mark.django_db

User = get_user_model()


@pytest.fixture(autouse=True)
def clear_registration_rate_cache():
    cache.clear()
    yield
    cache.clear()


def registration_payload(**overrides):
    payload = {
        "username": "new_seller",
        "email": "new-seller@example.com",
        "password": "StrongPass123!",
        "account_type": "seller",
    }
    payload.update(overrides)
    return payload


def test_register_creates_seller_from_account_type():
    client = APIClient()

    response = client.post("/api/auth/register/", registration_payload(), format="json")

    user = User.objects.get(username="new_seller")
    assert response.status_code == 201
    assert response.data["role"] == UserRole.SELLER
    assert response.data["email"] == "new-seller@example.com"
    assert "password" not in response.data
    assert user.role == UserRole.SELLER
    assert user.check_password("StrongPass123!")


def test_register_rejects_account_type_with_wrong_casing():
    client = APIClient()

    response = client.post(
        "/api/auth/register/",
        registration_payload(account_type="Seller"),
        format="json",
    )

    assert response.status_code == 400
    assert "account_type" in response.data
    assert not User.objects.filter(username="new_seller").exists()


def test_register_reports_duplicate_username_and_email():
    User.objects.create_user(
        username="new_seller",
        email="new-seller@example.com",
        password="StrongPass123!",
        role=UserRole.SELLER,
    )
    client = APIClient()

    response = client.post("/api/auth/register/", registration_payload(), format="json")

    assert response.status_code == 400
    assert "username" in response.data
    assert "email" in response.data


def test_register_reports_invalid_password():
    client = APIClient()

    response = client.post(
        "/api/auth/register/",
        registration_payload(password="short"),
        format="json",
    )

    assert response.status_code == 400
    assert "password" in response.data
