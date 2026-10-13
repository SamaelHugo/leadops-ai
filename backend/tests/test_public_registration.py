from __future__ import annotations

from app.config import get_settings


REGISTRATION = {
    "organization_name": "Northwind Demo",
    "organization_slug": "northwind-demo",
    "admin_name": "Demo Admin",
    "admin_email": "admin@northwind.example",
    "password": "a-long-enough-password",
}


def _reset_settings():
    get_settings.cache_clear()


def test_registration_open_by_default(client):
    _reset_settings()
    response = client.post("/api/auth/register", json=REGISTRATION)
    assert response.status_code == 201


def test_registration_closed_when_disabled(client, monkeypatch):
    """Публичное демо крутится на платных провайдерах, а рейт-лимита нет:
    открытый /register позволил бы любому посетителю индексировать документы
    и генерировать черновики за счёт владельца ключа."""
    monkeypatch.setenv("ALLOW_PUBLIC_REGISTRATION", "false")
    _reset_settings()
    try:
        response = client.post("/api/auth/register", json=REGISTRATION)
        assert response.status_code == 403
        assert "demo" in response.json()["detail"].lower()
    finally:
        monkeypatch.delenv("ALLOW_PUBLIC_REGISTRATION", raising=False)
        _reset_settings()
