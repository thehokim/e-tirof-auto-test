import requests
import json
import pytest
import time
from io import BytesIO
import os
from datetime import datetime

BASE_URL = "https://etirof.cmspace.uz/api"
LOGIN_URL = f"{BASE_URL}/auth/login"
CADASTRE_URL = f"{BASE_URL}/cadastre"

USER = {"username": "rool2", "password": "qwerty"}
FILE_PATH = "12636_2_230FF8971C606F9DCE94288E49178A0490EBD387.pdf"

@pytest.fixture(scope="session")
def pdf_file_content():
    if not os.path.exists(FILE_PATH):
        print(f" Файл не найден: {FILE_PATH}, используется заглушка.")
        return b"%PDF-1.7\n%Fake file for autotest\n%%EOF"
    with open(FILE_PATH, "rb") as f:
        return f.read()


@pytest.fixture(scope="session")
def jwt_headers():
    resp = requests.post(LOGIN_URL, json=USER)
    assert resp.status_code == 200, f"Ошибка логина: {resp.text}"
    data = resp.json()
    assert "token" in data, f"Нет токена в ответе: {data}"
    token = data["token"]
    role = data.get("role")
    print(f" Авторизован как {USER['username']}, роль: {role}")
    return {"Authorization": f"Bearer {token}"}


def test_1_get_cadastre_list(jwt_headers):
    resp = requests.get(CADASTRE_URL, headers=jwt_headers)
    assert resp.status_code == 200, f"Ошибка списка: {resp.text}"
    data = resp.json().get("data", [])
    print(f" Найдено {len(data)} кадастров")


def test_2_filter_by_region(jwt_headers):
    resp = requests.get(CADASTRE_URL, headers=jwt_headers, params={"region_soato": "1726"})
    assert resp.status_code == 200, f"Ошибка фильтрации: {resp.text}"
    data = resp.json().get("data", [])
    print(f" Фильтрация по региону успешна ({len(data)} записей)")


def test_3_get_invalid_cadastre(jwt_headers):
    resp = requests.get(f"{CADASTRE_URL}/9999999", headers=jwt_headers)
    assert resp.status_code in (404, 400)
    print(" Несуществующий кадастр корректно не найден.")


def test_4_unauthorized_access():
    resp = requests.get(CADASTRE_URL)
    assert resp.status_code == 401
    print(" Без токена корректно вернул 401 Unauthorized")


def test_5_wrong_token():
    fake_headers = {"Authorization": "Bearer BADTOKEN123"}
    resp = requests.get(CADASTRE_URL, headers=fake_headers)
    assert resp.status_code in (401, 403)
    print(f" Проверка неверного токена прошла ({resp.status_code})")


def test_6_verify_status(jwt_headers):
    resp = requests.get(f"{BASE_URL}/cadastre", headers=jwt_headers)
    assert resp.status_code == 200, f"Ошибка получения списка: {resp.text}"
    data = resp.json().get("data", [])
    if not data:
        pytest.skip("Нет кадастров для проверки статуса")

    first = data[0]
    cad_id = first.get("id") or first.get("ID")
    assert cad_id, "Нет ID кадастра"

    current_status = first.get("verification_status") or first.get("status") or "unknown"
    print(f" Текущий статус кадастра ID={cad_id}: {current_status}")

    payload = {
        "verified": True,
        "comment": f" Проверено verify {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    }

    resp_patch = requests.patch(f"{BASE_URL}/cadastre/{cad_id}/verification", headers=jwt_headers, json=payload)

    if resp_patch.status_code == 403:
        pytest.skip(" verify не имеет прав изменять статус (ожидаемо)")
    elif resp_patch.status_code == 404:
        pytest.skip(" Эндпоинт /verification не найден")
    else:
        assert resp_patch.status_code in (200, 202), f"Ошибка обновления статуса: {resp_patch.text}"
        print(f" Кадастр ID={cad_id} успешно отмечен как verified=True")

        resp_check = requests.get(f"{BASE_URL}/cadastre/{cad_id}", headers=jwt_headers)
        assert resp_check.status_code == 200
        updated_data = resp_check.json()
        new_status = (
            updated_data.get("verification_status")
            or updated_data.get("status")
            or updated_data.get("verified")
        )
        print(f" Новый статус после обновления: {new_status}")


def test_7_search_by_invalid_field(jwt_headers):
    resp = requests.get(CADASTRE_URL, headers=jwt_headers, params={"fake_field": "xxx"})
    assert resp.status_code in (200, 400)
    print(f" Сервер корректно обработал неизвестный фильтр ({resp.status_code})")


def test_8_response_time(jwt_headers):
    start = time.time()
    resp = requests.get(CADASTRE_URL, headers=jwt_headers)
    duration = time.time() - start
    assert duration < 3, f"Ответ слишком медленный: {duration:.2f}s"
    print(f" Время отклика API: {duration:.2f}s")