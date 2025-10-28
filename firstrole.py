import pytest
import requests

BASE_URL = "https://etirof.cmspace.uz/api"

users = [
    {"username": "rool1", "password": "qwerty"}
]

@pytest.mark.parametrize("user", users)
def test_login_users(user):
    """Проверяем, что пользователи rool1–5 могут успешно авторизоваться"""
    url = f"{BASE_URL}/auth/login"
    response = requests.post(url, json=user)
    assert response.status_code == 200, f"Ошибка логина {user['username']}: {response.text}"

    data = response.json()
    
    # Теперь проверяем правильное поле
    assert "token" in data, f"Нет токена у {user['username']}"
    assert "role" in data, f"Нет роли у {user['username']}"
    
    print(f"✅ {user['username']} вошёл как роль: {data['role']}")
