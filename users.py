import pytest
import requests
import random
import string

BASE_URL = "https://etirof.cmspace.uz/api/users"

@pytest.fixture(scope="session")
def root_token():
    auth_url = "https://etirof.cmspace.uz/api/auth/login"
    creds = {"username": "root", "password": "root"}
    resp = requests.post(auth_url, json=creds)
    assert resp.status_code == 200, f"Ошибка логина root: {resp.text}"
    token = resp.json().get("token")
    assert token, "Токен не найден"
    return token

def random_username():
    return "testuser_" + "".join(random.choices(string.ascii_lowercase, k=6))

@pytest.fixture
def headers(root_token):
    return {"Authorization": f"Bearer {root_token}", "Content-Type": "application/json"}

@pytest.fixture
def created_user(headers):
    payload = {
        "username": random_username(),
        "password": "Test123@",
        "firstName": "Auto",
        "middleName": "QA",
        "lastName": "Bot",
        "position": "tester",
        "active": True,
        "role": "cadastre_integration",
        "randomizerIndex": 1
    }
    resp = requests.post(BASE_URL, json=payload, headers=headers)
    assert resp.status_code == 201, f"Ошибка создания: {resp.text}"
    user = resp.json()["user"]
    yield user
    requests.delete(f"{BASE_URL}/{user['ID']}", headers=headers)

def test_create_user(created_user):
    assert created_user["username"].startswith("testuser_")
    assert created_user["active"] is True

def test_get_user(headers, created_user):
    user_id = created_user["ID"] 
    resp = requests.get(f"{BASE_URL}/{user_id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["ID"] == user_id 

def test_update_user(headers, created_user):
    user_id = created_user["ID"]
    new_name = "UpdatedName"
    payload = {"firstName": new_name}
    resp = requests.put(f"{BASE_URL}/{user_id}", json=payload, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["firstName"] == new_name

def test_toggle_user_status(headers, created_user):
    user_id = created_user["ID"]
    resp = requests.patch(f"{BASE_URL}/{user_id}/toggle-active", headers=headers)
    assert resp.status_code == 200
    new_state = resp.json()["active"]
    assert isinstance(new_state, bool)

def test_list_users(headers):
    resp = requests.get(BASE_URL, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "data" in data
    assert isinstance(data["data"], list)