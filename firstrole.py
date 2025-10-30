import requests
import json
import pytest
import time
from io import BytesIO
import os

# --- 🛠️ КОНФИГУРАЦИЯ PUSH-ИНТЕГРАЦИИ 🛠️ ---

BASE_URL = "https://etirof.cmspace.uz/api"
BASE_PUSH_URL = f"{BASE_URL}/cadastre/integration/push"
BASE_LIST_URL = f"{BASE_URL}/cadastre/integration" 
INTEGRATION_HEADERS = {"Authorization": "Basic Y2FkYXN0cmU6Y2FkNTY3QUFB"} 
FIRST_USER = {"username": "rool1", "password": "qwerty"}
FILE_PATH = "/home/user/Downloads/12636_2_230FF8971C606F9DCE94288E49178A0490EBD387.pdf"

# --- ФИКСТУРЫ И ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ (Перенесено из conftest.py) ---

@pytest.fixture(scope="session")
def pdf_file_content():
    """Чтение файла PDF для загрузки или возврат заглушки, если файл не найден."""
    if not os.path.exists(FILE_PATH):
        print(f"⚠️ ВНИМАНИЕ: Тестовый файл не найден по пути: {FILE_PATH}. Используется заглушка.")
        return b'%PDF-1.7\r\n%PDF-Test\r\n1 0 obj\n<< /Type /Catalog /Pages [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /MediaBox [0 0 612 792] >>\nendobj\n%%EOF'
    with open(FILE_PATH, "rb") as f:
        return f.read()

@pytest.fixture(scope="session")
def first_role_auth_headers():
    """Выполняет вход пользователя 'rool1' и возвращает заголовки Authorization (Bearer Token)."""
    url = f"{BASE_URL}/auth/login"
    
    response = requests.post(url, json=FIRST_USER)
    assert response.status_code == 200, f"Ошибка логина {FIRST_USER['username']}: {response.text}"
    
    data = response.json()
    token = data.get("token")
    role = data.get("role")

    assert token, f"Нет токена у {FIRST_USER['username']}"
    print(f"\n✅ {FIRST_USER['username']} вошёл как роль: {role} (Токен готов к использованию).")
    
    headers = {
        "Authorization": f"Bearer {token}", 
    }
    return headers


def find_cadastre_item(url, headers, unique_uid):
    """Вспомогательная функция для поиска элемента по кадастровому номеру."""
    search_params = {"cadastral_number": unique_uid} 
    search_response = requests.get(url, headers=headers, params=search_params)
    
    if search_response.status_code != 200:
        return None, search_response.status_code, search_response.text

    try:
        search_data = search_response.json()
    except json.JSONDecodeError:
        return None, search_response.status_code, "Неверный JSON ответ"
        
    items = search_data.get('results', []) or search_data.get('data', []) or search_data
    
    created_item = next((item for item in items if item.get("cadastreId") == unique_uid or item.get("uid") == unique_uid), None)
    
    if created_item:
        created_id = created_item.get("ID") or created_item.get("id") or created_item.get("uid") 
        return created_id, 200, None
        
    return None, 200, "Элемент не найден в списке"


@pytest.fixture(scope="session")
def created_cadastre_item_id(pdf_file_content, first_role_auth_headers):
    """
    Выполняет PUSH-запрос для создания элемента и возвращает его ID, 
    используя GET-запрос с Basic Auth и Fallback на Bearer Token.
    """
    unique_uid = f"test_auto_{int(time.time())}" 
    
    test_data_base = {
        "uidSPUnit": unique_uid,
        "cadastral_number": unique_uid, 
        "address": "Автоматический тест адрес",
        "land_fund_type_code": "10", 
        "land_use_type_code": "20", 
        "vid": "foo",
        "region_soato": "1726", 
        "district_soato": "1726264", 
        "neighborhood_soato": "1726264",
        "law_accordance_id": "1", 
        "selected_at": "2024-03-06 12:00:00",
        "step_deadline": "2024-03-10 12:00:00",
        # Геометрия 
        "location": {
            "type": "Polygon",
            "coordinates": [[[70.977547181, 40.742336418],[70.977609794, 40.742167422],[70.977411895, 40.74212747],[70.977547181, 40.742336418]]]
        }, 
        "mulk_egalari": [{"mulk_egasi": "A_Test", "mulk_egasi_stir": "111"}]
    }

    # Подготовка данных для multipart/form-data
    text_data = {k: v for k, v in test_data_base.items() if k not in ["location", "mulk_egalari"]}
    text_data["location"] = json.dumps(test_data_base["location"])
    text_data["mulk_egalari"] = json.dumps(test_data_base["mulk_egalari"])
    
    files = [(key, (None, value)) for key, value in text_data.items()]
    files.append(("building_land_cad_plan", ("land_plan.pdf", BytesIO(pdf_file_content), "application/pdf")))
    files.append(("governor_decree", ("decree.pdf", BytesIO(pdf_file_content), "application/pdf")))

    # 1. Выполняем PUSH-запрос
    response = requests.post(BASE_PUSH_URL, headers=INTEGRATION_HEADERS, files=files)
    
    if response.status_code != 201:
        pytest.fail(f"🔴 PUSH-запрос провален (Код {response.status_code}): {response.text}. Убедитесь, что Basic Auth верный.")

    # 2. Поиск ID через GET-запрос (попытка 1: Basic Auth)
    print(f"\n✅ PUSH успешен. Поиск ID по кадастровому номеру {unique_uid}...")
    
    created_id, status_code, error_message = find_cadastre_item(BASE_LIST_URL, INTEGRATION_HEADERS, unique_uid)
    
    if created_id:
        print(f"🎉 Элемент найден с ID: {created_id} с использованием Basic Auth.")
        return created_id
    
    if status_code == 401:
        # 3. Откат: Basic Auth не работает, пробуем Bearer Token 'rool1'
        print("⚠️ Basic Auth GET вернул 401. Повторная попытка с Bearer Token 'rool1'...")
        
        created_id, status_code_bearer, error_msg_bearer = find_cadastre_item(BASE_LIST_URL, first_role_auth_headers, unique_uid)
        
        if created_id:
            print(f"🎉 Элемент найден с ID: {created_id} с использованием Bearer Token.")
            return created_id
        else:
            pytest.fail(
                f"🔴 ID не найден даже с Bearer Token ({status_code_bearer}).\n"
                f"Ошибка Bearer Token GET: {error_msg_bearer}"
            )

    # 4. Сбой поиска Basic Auth, не 401
    pytest.fail(
        f"🔴 ID созданного элемента не найден после PUSH. GET-поиск Basic Auth вернул: Код {status_code}, Ошибка: {error_message}"
    )

# --- ТЕСТОВЫЕ ФУНКЦИИ ---

def test_update_screenshot(first_role_auth_headers, created_cadastre_item_id):
    """
    Тест: Обновление скриншота для созданного элемента.
    """
    cadastre_id = created_cadastre_item_id
    url = f"{BASE_URL}/cadastre/{cadastre_id}/screenshot"
    
    screenshot_payload = {
        "screenshot": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==",
        "file_name": f"{cadastre_id}_screenshot.png"
    }
    
    response = requests.patch(url, headers=first_role_auth_headers, json=screenshot_payload)
    
    assert response.status_code in [200, 202], f"Ошибка обновления скриншота для ID {cadastre_id}: Код {response.status_code}, Ответ: {response.text}"
    print(f"\n✅ Обновление скриншота для ID {cadastre_id} прошло успешно.")


def test_get_land_plan(first_role_auth_headers, created_cadastre_item_id):
    """
    Тест: Получение земельного плана (land plan) для созданного элемента.
    """
    cadastre_id = created_cadastre_item_id
    url = f"{BASE_URL}/cadastre/{cadastre_id}/land_plan"
    
    response = requests.get(url, headers=first_role_auth_headers)
    
    assert response.status_code == 200, f"Ошибка получения плана для ID {cadastre_id}: Код {response.status_code}, Ответ: {response.text}"
    
    assert len(response.content) > 100, "Ошибка: Полученный земельный план слишком мал или пуст."
    
    print(f"\n✅ Получение земельного плана для ID {cadastre_id} прошло успешно.")


def test_update_geometry_fix(first_role_auth_headers, created_cadastre_item_id):
    """
    Тест: Обновление скорректированной геометрии ('geometry_fix').
    """
    cadastre_id = created_cadastre_item_id
    url = f"{BASE_URL}/cadastre/{cadastre_id}/geometry_fix"
    
    fixed_geometry_payload = {
        "fixed_geojson": {
            "type": "Polygon",
            "coordinates": [[[70.977547181, 40.742336418],[70.977609794, 40.742167422],[70.977411895, 40.74212747],[70.977547181, 40.742336418]]]
        },
        "geometry_rotation": 5.0,
        "move_distance": 1.5,
        "space_image_id": "satellite_2025_01_01",
        "space_image_date": "2025-01-01T00:00:00Z",
        "edit_note": "Автоматическая коррекция геометрии."
    }

    response = requests.patch(url, headers=first_role_auth_headers, json=fixed_geometry_payload)

    assert response.status_code in [200, 202], f"Ошибка обновления геометрии для ID {cadastre_id}: Код {response.status_code}, Ответ: {response.text}"
    
    print(f"\n✅ Обновление скорректированной геометрии для ID {cadastre_id} прошло успешно.")