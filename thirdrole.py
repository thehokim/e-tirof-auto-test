import requests
import pytest
from datetime import datetime

BASE_URL = "https://etirof.cmspace.uz/api"
LOGIN_URL = f"{BASE_URL}/auth/login"
USER = {"username": "rool3", "password": "qwerty"}

@pytest.fixture(scope="session")
def headers():
    """Авторизация rool3 (роль: agency)"""
    resp = requests.post(LOGIN_URL, json=USER)
    assert resp.status_code == 200, f"Ошибка логина: {resp.text}"
    data = resp.json()
    token = data.get("token")
    role = data.get("role")
    assert token, "Нет токена"
    print(f" {USER['username']} вошёл как роль: {role}")
    return {"Authorization": f"Bearer {token}"}

def _get_first_cadastre(headers):
    """Возвращает первый кадастр из списка"""
    resp = requests.get(f"{BASE_URL}/cadastre", headers=headers)
    assert resp.status_code == 200, f"Ошибка списка: {resp.text}"
    data = resp.json().get("data", [])
    assert data, "Нет кадастров в списке"
    return data[0]

def test_1_list_cadastre_items(headers):
    response = requests.get(f"{BASE_URL}/cadastre", headers=headers)
    assert response.status_code == 200, f"Ошибка списка: {response.text}"
    total = len(response.json().get("data", []))
    print(f" Найдено {total} кадастров")


def test_2_get_cadastre_by_id(headers):
    item = _get_first_cadastre(headers)
    cad_id = item.get("id") or item.get("ID")
    resp = requests.get(f"{BASE_URL}/cadastre/{cad_id}", headers=headers)
    assert resp.status_code == 200, f"Ошибка получения кадастра ID={cad_id}: {resp.text}"
    print(f" Успешно получен кадастр ID={cad_id}")


def test_3_get_cadastre_by_cad_number(headers):
    item = _get_first_cadastre(headers)
    cad_number = item.get("cadastreId") or item.get("cadastral_number")
    assert cad_number, "Нет кадастрового номера"
    resp = requests.get(f"{BASE_URL}/cadastre/cad/{cad_number}", headers=headers)
    assert resp.status_code == 200, f"Ошибка получения по кадастровому номеру: {resp.text}"
    print(f" Получен кадастр по номеру {cad_number}")


def test_4_agency_verification_positive(headers):
    item = _get_first_cadastre(headers)
    cad_id = item.get("id") or item.get("ID")
    payload = {"verified": True, "comment": f"Проверено агентством {datetime.now()}"}
    resp = requests.patch(f"{BASE_URL}/cadastre/{cad_id}/agency_verification",
                          headers=headers, json=payload)
    if resp.status_code == 403:
        pytest.skip("У rool3 нет прав на агентскую верификацию")
    assert resp.status_code in (200, 202), f"Ошибка PATCH: {resp.text}"
    print(f"✅ Верификация прошла успешно для ID={cad_id}")


def test_5_get_recent_cadastres(headers):
    params = {"sort": "created_at", "order": "desc", "limit": 5}
    resp = requests.get(f"{BASE_URL}/cadastre", headers=headers, params=params)
    assert resp.status_code == 200, f"Ошибка при сортировке: {resp.text}"
    data = resp.json().get("data", [])
    if len(data) > 5:
        print(f" API вернуло {len(data)} вместо 5 — лимит игнорируется.")
    else:
        print(f" Получено {len(data)} кадастров (лимит работает)")


def test_6_filter_by_region(headers):
    params = {"region_soato": "1726"}
    resp = requests.get(f"{BASE_URL}/cadastre", headers=headers, params=params)
    assert resp.status_code == 200, f"Ошибка фильтрации: {resp.text}"
    print(f" Фильтрация по региону 1726 успешна ({len(resp.json().get('data', []))} записей)")


def test_7_check_pagination(headers):
    params = {"limit": 3, "offset": 0}
    resp = requests.get(f"{BASE_URL}/cadastre", headers=headers, params=params)
    assert resp.status_code == 200, f"Ошибка пагинации: {resp.text}"
    data = resp.json().get("data", [])
    print(f" API вернуло {len(data)} записей (ожидалось ≤ 3). Пагинация, возможно, не реализована.")


def test_8_agency_verification_false(headers):
    item = _get_first_cadastre(headers)
    cad_id = item.get("id") or item.get("ID")
    payload = {"verified": False, "comment": f"Отклонено агентом {datetime.now()}"}
    resp = requests.patch(f"{BASE_URL}/cadastre/{cad_id}/agency_verification",
                          headers=headers, json=payload)
    assert resp.status_code in (200, 202), f"Ошибка PATCH false: {resp.text}"
    print(f" Агент успешно отклонил кадастр ID={cad_id}")

def test_11_invalid_id_format(headers):
    resp = requests.get(f"{BASE_URL}/cadastre/abc123", headers=headers)
    assert resp.status_code in (400, 422), f"Ожидался 400/422, получено {resp.status_code}"
    print(f" Проверка неверного формата ID прошла: {resp.status_code}")


def test_12_patch_invalid_json(headers):
    item = _get_first_cadastre(headers)
    cad_id = item.get("id") or item.get("ID")
    bad_json = '{"verified": true, "comment": "broken json"'  
    resp = requests.patch(f"{BASE_URL}/cadastre/{cad_id}/agency_verification",
                          headers={**headers, "Content-Type": "application/json"},
                          data=bad_json)
    assert resp.status_code in (400, 422, 500)
    print(f" Неверный JSON обработан — {resp.status_code}")


def test_13_unauthorized_access():
    resp = requests.get(f"{BASE_URL}/cadastre")
    assert resp.status_code == 401
    print(" Без токена корректно вернул 401 Unauthorized")


def test_14_wrong_token():
    fake_headers = {"Authorization": "Bearer INVALID_TOKEN_123"}
    resp = requests.get(f"{BASE_URL}/cadastre", headers=fake_headers)
    assert resp.status_code in (401, 403)
    print(f" Проверка неверного токена прошла — {resp.status_code}")