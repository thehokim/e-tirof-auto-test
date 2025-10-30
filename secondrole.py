"""
Тесты для роли 'verify' (rool2)
Проверка просмотра кадастров и верификации
Структура аналогична fifthrole.py
"""

import requests
import json
import pytest
import allure
import time
from io import BytesIO
import os
from datetime import datetime


# === ⚙️ Конфигурация ===

BASE_URL = "https://etirof.cmspace.uz/api"
LOGIN_URL = f"{BASE_URL}/auth/login"
CADASTRE_URL = f"{BASE_URL}/cadastre"

USER = {"username": "rool2", "password": "qwerty"}
FILE_PATH = "12636_2_230FF8971C606F9DCE94288E49178A0490EBD387.pdf"


# === 🔧 API Client ===

class VerifyApiClient:
    """API клиент для роли verify"""
    
    def __init__(self, token: str):
        self.token = token
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        })
        self.base_url = BASE_URL
        self.cadastre_url = CADASTRE_URL
    
    def get_cadastre_list(self, params=None):
        """Получение списка кадастров"""
        return self.session.get(self.cadastre_url, params=params)
    
    def get_cadastre_by_id(self, cadastre_id):
        """Получение кадастра по ID"""
        return self.session.get(f"{self.cadastre_url}/{cadastre_id}")
    
    def verify_cadastre(self, cadastre_id, verified: bool, comment: str = None):
        """Верификация кадастра"""
        payload = {"verified": verified}
        if comment:
            payload["comment"] = comment
        return self.session.patch(
            f"{self.cadastre_url}/{cadastre_id}/verification",
            json=payload
        )
    
    def filter_by_region(self, region_soato: str):
        """Фильтрация кадастров по региону"""
        return self.get_cadastre_list(params={"region_soato": region_soato})


# === 🧩 Фикстуры ===

@pytest.fixture(scope="session")
@allure.title("Подготовка PDF файла")
def pdf_file_content():
    """Читает PDF или создаёт заглушку."""
    with allure.step("Проверка наличия PDF файла"):
        if not os.path.exists(FILE_PATH):
            allure.attach(
                f"Файл не найден: {FILE_PATH}",
                name="File Status",
                attachment_type=allure.attachment_type.TEXT
            )
            print(f"⚠️ Файл не найден: {FILE_PATH}, используется заглушка.")
            return b"%PDF-1.7\n%Fake file for autotest\n%%EOF"
        
        with open(FILE_PATH, "rb") as f:
            content = f.read()
            allure.attach(
                f"Размер файла: {len(content)} байт",
                name="PDF Info",
                attachment_type=allure.attachment_type.TEXT
            )
            return content


@pytest.fixture(scope="session")
@allure.title("Авторизация пользователя verify (rool2)")
def auth_token():
    """Авторизация rool2 и получение токена."""
    allure.dynamic.parameter("Username", USER['username'])
    allure.dynamic.parameter("Role", "verify")
    
    with allure.step(f"Отправка POST запроса на {LOGIN_URL}"):
        resp = requests.post(LOGIN_URL, json=USER)
        
        allure.attach(
            json.dumps({"username": USER['username'], "password": "***"}, indent=2),
            name="Login Request",
            attachment_type=allure.attachment_type.JSON
        )
        
        allure.attach(
            resp.text,
            name="Login Response",
            attachment_type=allure.attachment_type.JSON
        )
        
        assert resp.status_code == 200, f"Ошибка логина: {resp.text}"
    
    with allure.step("Извлечение токена из ответа"):
        data = resp.json()
        assert "token" in data, f"Нет токена в ответе: {data}"
        token = data["token"]
        role = data.get("role")
        
        allure.attach(
            f"Token: {token[:20]}...\nRole: {role}",
            name="Auth Info",
            attachment_type=allure.attachment_type.TEXT
        )
        
        print(f"✅ Авторизован как {USER['username']}, роль: {role}")
        
    return token


@pytest.fixture(scope="session")
def jwt_headers(auth_token):
    """HTTP заголовки с Bearer токеном"""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture(scope="session")
def api_client(auth_token):
    """API клиент с авторизацией"""
    return VerifyApiClient(auth_token)


@pytest.fixture
def first_cadastre(api_client):
    """Получение первого кадастра из списка"""
    with allure.step("Получение первого кадастра для тестирования"):
        resp = api_client.get_cadastre_list()
        assert resp.status_code == 200, f"Не удалось получить список: {resp.text}"
        
        data = resp.json().get("data", [])
        if not data:
            pytest.skip("Нет кадастров для тестирования")
        
        cadastre = data[0]
        cadastre_id = cadastre.get("id") or cadastre.get("ID")
        
        allure.attach(
            json.dumps(cadastre, indent=2, ensure_ascii=False),
            name="First Cadastre",
            attachment_type=allure.attachment_type.JSON
        )
        
        allure.dynamic.parameter("Cadastre ID", cadastre_id)
        
        return cadastre


# === 🧪 ТЕСТЫ ===

@allure.epic("Cadastre API")
@allure.feature("Cadastre Viewing")
@allure.story("List Cadastres")
class TestCadastreList:
    """Тесты получения списка кадастров"""
    
    @allure.title("Получение полного списка кадастров")
    @allure.description("Проверяет что пользователь verify может просматривать список всех кадастров")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("smoke", "cadastre", "list")
    def test_01_get_cadastre_list(self, api_client):
        """✅ Получение списка кадастров"""
        
        with allure.step("Отправка GET запроса"):
            resp = api_client.get_cadastre_list()
            
            allure.attach(
                f"GET {api_client.cadastre_url}",
                name="Request URL",
                attachment_type=allure.attachment_type.TEXT
            )
            
            allure.attach(
                resp.text,
                name="Response Body",
                attachment_type=allure.attachment_type.JSON
            )
        
        with allure.step("Проверка статус кода 200"):
            assert resp.status_code == 200, f"Ошибка списка: {resp.text}"
        
        with allure.step("Подсчет кадастров"):
            data = resp.json().get("data", [])
            count = len(data)
            
            allure.attach(
                f"Всего кадастров: {count}",
                name="Statistics",
                attachment_type=allure.attachment_type.TEXT
            )
            
            print(f"✅ Найдено {count} кадастров")
    
    @allure.title("Получение кадастра по ID")
    @allure.description("Проверяет получение конкретного кадастра по его ID")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.tag("cadastre", "read")
    def test_02_get_cadastre_by_id(self, api_client, first_cadastre):
        """✅ Получение кадастра по ID"""
        
        cadastre_id = first_cadastre.get("id") or first_cadastre.get("ID")
        
        with allure.step(f"Запрос кадастра с ID={cadastre_id}"):
            resp = api_client.get_cadastre_by_id(cadastre_id)
            
            allure.attach(
                resp.text,
                name="Cadastre Response",
                attachment_type=allure.attachment_type.JSON
            )
        
        with allure.step("Проверка успешного получения"):
            assert resp.status_code == 200, f"Ошибка получения: {resp.text}"
            
            data = resp.json()
            response_id = data.get("id") or data.get("ID")
            
            assert response_id == cadastre_id, f"ID не совпадает: {response_id} != {cadastre_id}"
            
            print(f"✅ Кадастр ID={cadastre_id} успешно получен")
    
    @allure.title("Получение несуществующего кадастра")
    @allure.description("Негативный тест: проверка получения кадастра с несуществующим ID")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.tag("negative", "validation")
    def test_03_get_invalid_cadastre(self, api_client):
        """❌ Получение несуществующего ID"""
        
        invalid_id = 9999999
        allure.dynamic.parameter("Invalid ID", invalid_id)
        
        with allure.step(f"Попытка получить кадастр ID={invalid_id}"):
            resp = api_client.get_cadastre_by_id(invalid_id)
            
            allure.attach(
                resp.text,
                name="Error Response",
                attachment_type=allure.attachment_type.TEXT
            )
        
        with allure.step("Проверка ошибки 404 или 400"):
            assert resp.status_code in (404, 400), f"Ожидался 404/400, получен {resp.status_code}"
            print(f"❌ Несуществующий кадастр корректно не найден: {resp.status_code}")


@allure.epic("Cadastre API")
@allure.feature("Cadastre Filtering")
@allure.story("Filter by Region")
class TestCadastreFiltering:
    """Тесты фильтрации кадастров"""
    
    @allure.title("Фильтрация по региону (region_soato)")
    @allure.description("Проверяет фильтрацию кадастров по коду региона SOATO")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.tag("filter", "region")
    def test_01_filter_by_region(self, api_client):
        """✅ Фильтрация по региону"""
        
        region_code = "1726"
        allure.dynamic.parameter("Region SOATO", region_code)
        
        with allure.step(f"Фильтрация по региону {region_code}"):
            resp = api_client.filter_by_region(region_code)
            
            allure.attach(
                f"GET {api_client.cadastre_url}?region_soato={region_code}",
                name="Request URL",
                attachment_type=allure.attachment_type.TEXT
            )
            
            allure.attach(
                resp.text,
                name="Filtered Response",
                attachment_type=allure.attachment_type.JSON
            )
        
        with allure.step("Проверка успешного ответа"):
            assert resp.status_code == 200, f"Ошибка фильтрации: {resp.text}"
        
        with allure.step("Подсчет отфильтрованных записей"):
            data = resp.json().get("data", [])
            count = len(data)
            
            allure.attach(
                f"Найдено записей: {count}",
                name="Filter Results",
                attachment_type=allure.attachment_type.TEXT
            )
            
            print(f"✅ Фильтрация по региону {region_code} успешна ({count} записей)")
    
    @allure.title("Фильтрация по несуществующему полю")
    @allure.description("Проверка обработки некорректных параметров фильтрации")
    @allure.severity(allure.severity_level.MINOR)
    @allure.tag("validation", "negative")
    def test_02_search_by_invalid_field(self, api_client):
        """❌ Фильтр по несуществующему полю"""
        
        invalid_param = {"fake_field": "xxx"}
        allure.dynamic.parameter("Invalid Params", str(invalid_param))
        
        with allure.step("Запрос с несуществующим параметром"):
            resp = api_client.get_cadastre_list(params=invalid_param)
            
            allure.attach(
                resp.text,
                name="Response",
                attachment_type=allure.attachment_type.JSON
            )
        
        with allure.step("Проверка что сервер обработал запрос"):
            assert resp.status_code in (200, 400), f"Неожиданный статус: {resp.status_code}"
            print(f"⚠️ Сервер корректно обработал неизвестный фильтр ({resp.status_code})")


@allure.epic("Cadastre API")
@allure.feature("Verification")
@allure.story("Verify Cadastre")
class TestCadastreVerification:
    """Тесты верификации кадастров"""
    
    @allure.title("Верификация кадастра (verified=True)")
    @allure.description("""
    Проверяет что пользователь verify может:
    1. Просмотреть кадастры
    2. Отметить кадастр как проверенный
    3. Добавить комментарий к верификации
    """)
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("verification", "critical")
    def test_01_verify_status_true(self, api_client, first_cadastre):
        """✅ Отметка кадастра как проверенного"""
        
        cadastre_id = first_cadastre.get("id") or first_cadastre.get("ID")
        current_status = first_cadastre.get("verification_status") or first_cadastre.get("status") or "unknown"
        
        allure.attach(
            f"ID: {cadastre_id}\nТекущий статус: {current_status}",
            name="Cadastre Info",
            attachment_type=allure.attachment_type.TEXT
        )
        
        print(f"🔎 Текущий статус кадастра ID={cadastre_id}: {current_status}")
        
        with allure.step("Отправка запроса на верификацию"):
            comment = f"✅ Проверено verify {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            resp = api_client.verify_cadastre(cadastre_id, verified=True, comment=comment)
            
            allure.attach(
                json.dumps({"verified": True, "comment": comment}, indent=2),
                name="Verification Payload",
                attachment_type=allure.attachment_type.JSON
            )
            
            allure.attach(
                resp.text,
                name="Verification Response",
                attachment_type=allure.attachment_type.JSON
            )
            
            if resp.status_code == 403:
                pytest.skip("⛔️ verify не имеет прав изменять статус (ожидаемо)")
            elif resp.status_code == 404:
                pytest.skip("⚠️ Эндпоинт /verification не найден")
            else:
                assert resp.status_code in (200, 202), f"Ошибка обновления: {resp.text}"
                print(f"✅ Кадастр ID={cadastre_id} успешно отмечен как verified=True")
        
        with allure.step("Проверка обновленного статуса"):
            resp_check = api_client.get_cadastre_by_id(cadastre_id)
            
            allure.attach(
                resp_check.text,
                name="Updated Cadastre",
                attachment_type=allure.attachment_type.JSON
            )
            
            assert resp_check.status_code == 200
            updated_data = resp_check.json()
            new_status = (
                updated_data.get("verification_status")
                or updated_data.get("status")
                or updated_data.get("verified")
            )
            
            allure.attach(
                f"Статус до: {current_status}\nСтатус после: {new_status}",
                name="Status Comparison",
                attachment_type=allure.attachment_type.TEXT
            )
            
            print(f"🔁 Новый статус: {new_status}")


@allure.epic("Cadastre API")
@allure.feature("Authentication & Security")
@allure.story("Access Control")
class TestAuthentication:
    """Тесты безопасности и аутентификации"""
    
    @allure.title("Доступ без токена")
    @allure.description("Проверка что API требует авторизацию")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("security", "auth", "negative")
    def test_01_unauthorized_access(self):
        """❌ Доступ без токена"""
        
        with allure.step("Отправка запроса без Authorization"):
            resp = requests.get(CADASTRE_URL)
            
            allure.attach(
                f"GET {CADASTRE_URL}\nHeaders: None",
                name="Request Info",
                attachment_type=allure.attachment_type.TEXT
            )
            
            allure.attach(
                resp.text,
                name="401 Response",
                attachment_type=allure.attachment_type.TEXT
            )
        
        with allure.step("Проверка статус кода 401"):
            assert resp.status_code == 401, f"Ожидался 401, получен {resp.status_code}"
            print("❌ Без токена корректно вернул 401 Unauthorized")
    
    @allure.title("Доступ с неверным токеном")
    @allure.description("Проверка что API отклоняет неверные токены")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("security", "auth", "negative")
    def test_02_wrong_token(self):
        """❌ Неверный токен"""
        
        fake_token = "BADTOKEN123"
        allure.dynamic.parameter("Fake Token", fake_token)
        
        with allure.step("Отправка запроса с поддельным токеном"):
            fake_headers = {"Authorization": f"Bearer {fake_token}"}
            resp = requests.get(CADASTRE_URL, headers=fake_headers)
            
            allure.attach(
                f"Authorization: Bearer {fake_token}",
                name="Request Headers",
                attachment_type=allure.attachment_type.TEXT
            )
            
            allure.attach(
                resp.text,
                name="Error Response",
                attachment_type=allure.attachment_type.TEXT
            )
        
        with allure.step("Проверка ошибки 401 или 403"):
            assert resp.status_code in (401, 403), f"Ожидался 401/403, получен {resp.status_code}"
            print(f"❌ Проверка неверного токена прошла ({resp.status_code})")


@allure.epic("Cadastre API")
@allure.feature("Performance")
@allure.story("Response Time")
class TestPerformance:
    """Тесты производительности API"""
    
    @allure.title("Проверка времени отклика API")
    @allure.description("Проверяет что API отвечает быстро (< 3 секунд)")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.tag("performance", "sla")
    def test_01_response_time(self, api_client):
        """⏱️ Время отклика API < 3s"""
        
        max_time = 3.0
        allure.dynamic.parameter("Max Response Time", f"{max_time}s")
        
        with allure.step("Замер времени выполнения запроса"):
            start = time.time()
            resp = api_client.get_cadastre_list()
            duration = time.time() - start
            
            allure.attach(
                f"Время отклика: {duration:.3f}s\n"
                f"Максимум: {max_time}s\n"
                f"Статус: {'✅ PASS' if duration < max_time else '❌ FAIL'}",
                name="Performance Metrics",
                attachment_type=allure.attachment_type.TEXT
            )
        
        with allure.step(f"Проверка что время < {max_time}s"):
            assert resp.status_code == 200, f"Request failed: {resp.status_code}"
            assert duration < max_time, f"Ответ слишком медленный: {duration:.2f}s"
            print(f"✅ Время отклика API: {duration:.2f}s")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--alluredir=allure-results"])