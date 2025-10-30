import pytest
import requests

BASE_URL = "https://etirof.cmspace.uz/api"

users_positive = [
    {"username": "root", "password": "root"},  
]

users_negative = [
    {"username": "root", "password": "wrongpass"},     
    {"username": "not_exist", "password": "123456"},    
    {"username": "", "password": ""},                  
    {"username": "a" * 256, "password": "a" * 256},    
]

@pytest.mark.parametrize("user", users_positive)
def test_login_success(user):
    url = f"{BASE_URL}/auth/login"
    response = requests.post(url, json=user)
    assert response.status_code == 200, f"Ошибка логина {user['username']}: {response.text}"
    data = response.json()
    assert "token" in data, f"Нет токена у {user['username']}"
    assert "role" in data, f"Нет роли у {user['username']}"
    print(f" {user['username']} вошёл как {data['role']}")


@pytest.mark.parametrize("user", users_negative)
def test_login_fail(user):
    url = f"{BASE_URL}/auth/login"
    response = requests.post(url, json=user)
    assert response.status_code in [400, 401, 404, 422], (
        f"Ожидали ошибку при {user}, но получили {response.status_code}: {response.text}"
    )

    print(f" Проверка неуспешного входа {user['username']} прошла — код {response.status_code}")

def test_login_invalid_json():
    url = f"{BASE_URL}/auth/login"
    response = requests.post(url, data="{invalid_json")

    assert response.status_code in [400, 422], f"Ожидали ошибку, но получили {response.status_code}"
    print(" Проверка с невалидным JSON прошла успешно")
