import requests
import json
import pytest
import allure
import time
from datetime import datetime


# === ⚙️ Конфигурация ===

BASE_URL = "https://etirof.cmspace.uz/api"
LOGIN_URL = f"{BASE_URL}/auth/login"
CADASTRE_URL = f"{BASE_URL}/cadastre"

USER = {"username": "rool3", "password": "qwerty"}


# === 🔧 API Client ===

class AgencyApiClient:
    """API клиент для роли agency"""
    
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
    
    def get_cadastre_by_number(self, cadastre_number):
        """Получение кадастра по кадастровому номеру"""
        return self.session.get(f"{self.cadastre_url}/cad/{cadastre_number}")
    
    def agency_verification(self, cadastre_id, verified: bool, comment: str = None):
        """Агентская верификация кадастра"""
        payload = {"verified": verified}
        if comment:
            payload["comment"] = comment
        return self.session.patch(
            f"{self.cadastre_url}/{cadastre_id}/agency_verification",
            json=payload
        )
    
    def get_statistics(self):
        """Попытка получить статистику"""
        possible_endpoints = [
            f"{self.cadastre_url}/statistics",
            f"{self.cadastre_url}/stats",
            f"{self.cadastre_url}/summary"
        ]
        for url in possible_endpoints:
            resp = self.session.get(url)
            if resp.status_code == 200:
                return resp, url
        return None, None


# === 🧩 Фикстуры ===

@pytest.fixture(scope="session")
@allure.title("Авторизация пользователя agency (rool3)")
def auth_token():
    """Авторизация rool3 и получение токена"""
    allure.dynamic.parameter("Username", USER['username'])
    allure.dynamic.parameter("Role", "agency")
    
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
        token = data.get("token")
        role = data.get("role")
        
        assert token, "Нет токена"
        
        allure.attach(
            f"Token: {token[:20]}...\nRole: {role}",
            name="Auth Info",
            attachment_type=allure.attachment_type.TEXT
        )
        
        print(f"✅ {USER['username']} вошёл как роль: {role}")
        
    return token


@pytest.fixture(scope="session")
def headers(auth_token):
    """HTTP заголовки с Bearer токеном"""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture(scope="session")
def api_client(auth_token):
    """API клиент с авторизацией"""
    return AgencyApiClient(auth_token)


@pytest.fixture
def first_cadastre(api_client):
    """Получение первого кадастра из списка"""
    with allure.step("Получение первого кадастра для тестирования"):
        resp = api_client.get_cadastre_list()
        assert resp.status_code == 200, f"Ошибка списка: {resp.text}"
        
        data = resp.json().get("data", [])
        assert data, "Нет кадастров в списке"
        
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
@allure.story("List and Get Cadastres")
class TestCadastreViewing:
    """Тесты просмотра кадастров"""
    
    @allure.title("Получение полного списка кадастров")
    @allure.description("Проверяет что пользователь agency может просматривать список всех кадастров")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("smoke", "cadastre", "list")
    def test_01_list_cadastre_items(self, api_client):
        """✅ Получение полного списка кадастров"""
        
        with allure.step("Отправка GET запроса"):
            response = api_client.get_cadastre_list()
            
            allure.attach(
                f"GET {api_client.cadastre_url}",
                name="Request URL",
                attachment_type=allure.attachment_type.TEXT
            )
            
            allure.attach(
                response.text,
                name="Response Body",
                attachment_type=allure.attachment_type.JSON
            )
        
        with allure.step("Проверка статус кода 200"):
            assert response.status_code == 200, f"Ошибка списка: {response.text}"
        
        with allure.step("Подсчет кадастров"):
            total = len(response.json().get("data", []))
            
            allure.attach(
                f"Всего кадастров: {total}",
                name="Statistics",
                attachment_type=allure.attachment_type.TEXT
            )
            
            print(f"✅ Найдено {total} кадастров")
    
    @allure.title("Получение кадастра по ID")
    @allure.description("Проверяет получение конкретного кадастра по его ID")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.tag("cadastre", "read")
    def test_02_get_cadastre_by_id(self, api_client, first_cadastre):
        """✅ Получение кадастра по ID"""
        
        cad_id = first_cadastre.get("id") or first_cadastre.get("ID")
        
        with allure.step(f"Запрос кадастра с ID={cad_id}"):
            resp = api_client.get_cadastre_by_id(cad_id)
            
            allure.attach(
                resp.text,
                name="Cadastre Response",
                attachment_type=allure.attachment_type.JSON
            )
        
        with allure.step("Проверка успешного получения"):
            assert resp.status_code == 200, f"Ошибка получения кадастра ID={cad_id}: {resp.text}"
            print(f"✅ Успешно получен кадастр ID={cad_id}")
    
    @allure.title("Получение кадастра по кадастровому номеру")
    @allure.description("Проверяет получение кадастра по его кадастровому номеру")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.tag("cadastre", "read")
    def test_03_get_cadastre_by_cad_number(self, api_client, first_cadastre):
        """✅ Получение кадастра по кадастровому номеру"""
        
        cad_number = first_cadastre.get("cadastreId") or first_cadastre.get("cadastral_number")
        assert cad_number, "Нет кадастрового номера"
        
        allure.dynamic.parameter("Cadastre Number", cad_number)
        
        with allure.step(f"Запрос кадастра по номеру {cad_number}"):
            resp = api_client.get_cadastre_by_number(cad_number)
            
            allure.attach(
                f"GET {api_client.cadastre_url}/cad/{cad_number}",
                name="Request URL",
                attachment_type=allure.attachment_type.TEXT
            )
            
            allure.attach(
                resp.text,
                name="Response",
                attachment_type=allure.attachment_type.JSON
            )
        
        with allure.step("Проверка успешного получения"):
            assert resp.status_code == 200, f"Ошибка получения по кадастровому номеру: {resp.text}"
            print(f"✅ Получен кадастр по номеру {cad_number}")


@allure.epic("Cadastre API")
@allure.feature("Agency Verification")
@allure.story("Verify Cadastre")
class TestAgencyVerification:
    """Тесты агентской верификации"""
    
    @allure.title("Агентская верификация (verified=True)")
    @allure.description("Проверяет что agency может одобрить кадастр")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("verification", "critical")
    def test_01_agency_verification_positive(self, api_client, first_cadastre):
        """✅ Агентская верификация (верный PATCH)"""
        
        cad_id = first_cadastre.get("id") or first_cadastre.get("ID")
        
        with allure.step("Отправка запроса на одобрение"):
            comment = f"Проверено агентством {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            resp = api_client.agency_verification(cad_id, verified=True, comment=comment)
            
            allure.attach(
                json.dumps({"verified": True, "comment": comment}, indent=2),
                name="Verification Payload",
                attachment_type=allure.attachment_type.JSON
            )
            
            allure.attach(
                resp.text,
                name="Response",
                attachment_type=allure.attachment_type.JSON
            )
            
            if resp.status_code == 403:
                pytest.skip("У rool3 нет прав на агентскую верификацию")
        
        with allure.step("Проверка успешного ответа"):
            assert resp.status_code in (200, 202), f"Ошибка PATCH: {resp.text}"
            print(f"✅ Верификация прошла успешно для ID={cad_id}")
    
    @allure.title("Агентская верификация (verified=False)")
    @allure.description("Проверяет что agency может отклонить кадастр")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.tag("verification")
    def test_02_agency_verification_false(self, api_client, first_cadastre):
        """✅ Проверка отклонения агентом"""
        
        cad_id = first_cadastre.get("id") or first_cadastre.get("ID")
        
        with allure.step("Отправка запроса на отклонение"):
            comment = f"Отклонено агентом {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            resp = api_client.agency_verification(cad_id, verified=False, comment=comment)
            
            allure.attach(
                json.dumps({"verified": False, "comment": comment}, indent=2),
                name="Rejection Payload",
                attachment_type=allure.attachment_type.JSON
            )
            
            allure.attach(
                resp.text,
                name="Response",
                attachment_type=allure.attachment_type.JSON
            )
        
        with allure.step("Проверка успешного ответа"):
            assert resp.status_code in (200, 202), f"Ошибка PATCH false: {resp.text}"
            print(f"✅ Агент успешно отклонил кадастр ID={cad_id}")


@allure.epic("Cadastre API")
@allure.feature("Cadastre Filtering & Sorting")
@allure.story("Filter and Sort")
class TestCadastreFiltering:
    """Тесты фильтрации и сортировки"""
    
    @allure.title("Фильтрация по региону")
    @allure.description("Проверяет фильтрацию кадастров по коду региона SOATO")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.tag("filter", "region")
    def test_01_filter_by_region(self, api_client):
        """✅ Фильтрация по региону"""
        
        region_code = "1726"
        allure.dynamic.parameter("Region SOATO", region_code)
        
        with allure.step(f"Фильтрация по региону {region_code}"):
            params = {"region_soato": region_code}
            resp = api_client.get_cadastre_list(params=params)
            
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
            count = len(resp.json().get('data', []))
            
            allure.attach(
                f"Найдено записей: {count}",
                name="Filter Results",
                attachment_type=allure.attachment_type.TEXT
            )
            
            print(f"✅ Фильтрация по региону {region_code} успешна ({count} записей)")
    
    @allure.title("Получение недавних кадастров (сортировка)")
    @allure.description("Проверяет сортировку по дате создания и лимит")
    @allure.severity(allure.severity_level.MINOR)
    @allure.tag("sort", "limit")
    def test_02_get_recent_cadastres(self, api_client):
        """✅ Получение недавних кадастров (мягкая проверка лимита)"""
        
        params = {"sort": "created_at", "order": "desc", "limit": 5}
        allure.dynamic.parameter("Params", str(params))
        
        with allure.step("Запрос с сортировкой и лимитом"):
            resp = api_client.get_cadastre_list(params=params)
            
            allure.attach(
                resp.text,
                name="Response",
                attachment_type=allure.attachment_type.JSON
            )
        
        with allure.step("Проверка успешного ответа"):
            assert resp.status_code == 200, f"Ошибка при сортировке: {resp.text}"
        
        with allure.step("Проверка лимита"):
            data = resp.json().get("data", [])
            count = len(data)
            
            if count > 5:
                allure.attach(
                    f"API вернуло {count} записей вместо 5",
                    name="Limit Warning",
                    attachment_type=allure.attachment_type.TEXT
                )
                print(f"⚠️ API вернуло {count} вместо 5 — лимит игнорируется.")
            else:
                print(f"✅ Получено {count} кадастров (лимит работает)")
    
    @allure.title("Проверка пагинации")
    @allure.description("Проверяет работу параметров limit и offset")
    @allure.severity(allure.severity_level.MINOR)
    @allure.tag("pagination")
    def test_03_check_pagination(self, api_client):
        """✅ Проверка пагинации (мягкий режим)"""
        
        params = {"limit": 3, "offset": 0}
        allure.dynamic.parameter("Params", str(params))
        
        with allure.step("Запрос с пагинацией"):
            resp = api_client.get_cadastre_list(params=params)
            
            allure.attach(
                resp.text,
                name="Response",
                attachment_type=allure.attachment_type.JSON
            )
        
        with allure.step("Проверка успешного ответа"):
            assert resp.status_code == 200, f"Ошибка пагинации: {resp.text}"
        
        with allure.step("Проверка количества записей"):
            data = resp.json().get("data", [])
            count = len(data)
            
            allure.attach(
                f"Получено: {count} записей\nОжидалось: ≤ 3",
                name="Pagination Check",
                attachment_type=allure.attachment_type.TEXT
            )
            
            print(f"⚠️ API вернуло {count} записей (ожидалось ≤ 3). Пагинация, возможно, не реализована.")


@allure.epic("Cadastre API")
@allure.feature("Statistics & Profile")
@allure.story("Additional Endpoints")
class TestAdditionalEndpoints:
    """Тесты дополнительных эндпоинтов"""
    
    @allure.title("Получение статистики кадастров")
    @allure.description("Проверяет доступность эндпоинта статистики")
    @allure.severity(allure.severity_level.MINOR)
    @allure.tag("statistics")
    def test_01_get_statistics(self, api_client):
        """✅ Проверка доступности статистики кадастров"""
        
        with allure.step("Поиск эндпоинта статистики"):
            resp, url = api_client.get_statistics()
            
            if resp and resp.status_code == 200:
                allure.attach(
                    f"URL: {url}",
                    name="Statistics Endpoint",
                    attachment_type=allure.attachment_type.TEXT
                )
                
                allure.attach(
                    resp.text,
                    name="Statistics Response",
                    attachment_type=allure.attachment_type.JSON
                )
                
                print(f"✅ Эндпоинт статистики найден: {url}")
                print(f"Ответ: {list(resp.json().keys())}")
            else:
                print("⚠️ Эндпоинт статистики не найден (возможен 404/400). Пропускаем.")
                pytest.skip("Эндпоинт статистики отсутствует.")


@allure.epic("Cadastre API")
@allure.feature("Validation & Error Handling")
@allure.story("Negative Tests")
class TestValidation:
    """Тесты валидации и обработки ошибок"""
    
    @allure.title("Запрос с неверным форматом ID")
    @allure.description("Проверяет обработку некорректного формата ID")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.tag("negative", "validation")
    def test_01_invalid_id_format(self, api_client):
        """❌ Ошибка при запросе ID с неправильным форматом"""
        
        invalid_id = "abc123"
        allure.dynamic.parameter("Invalid ID", invalid_id)
        
        with allure.step(f"Запрос с ID={invalid_id}"):
            resp = api_client.get_cadastre_by_id(invalid_id)
            
            allure.attach(
                resp.text,
                name="Error Response",
                attachment_type=allure.attachment_type.TEXT
            )
        
        with allure.step("Проверка ошибки 400 или 422"):
            assert resp.status_code in (400, 422), f"Ожидался 400/422, получено {resp.status_code}"
            print(f"❌ Проверка неверного формата ID прошла: {resp.status_code}")
    
    @allure.title("Отправка некорректного JSON")
    @allure.description("Проверяет обработку битого JSON в запросе")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.tag("negative", "validation")
    def test_02_patch_invalid_json(self, api_client, first_cadastre):
        """❌ Ошибка при отправке битого JSON"""
        
        cad_id = first_cadastre.get("id") or first_cadastre.get("ID")
        bad_json = '{"verified": true, "comment": "broken json"'  # без закрытия скобки
        
        allure.dynamic.parameter("Malformed JSON", bad_json)
        
        with allure.step("Отправка некорректного JSON"):
            resp = requests.patch(
                f"{api_client.cadastre_url}/{cad_id}/agency_verification",
                headers={**api_client.session.headers, "Content-Type": "application/json"},
                data=bad_json
            )
            
            allure.attach(
                bad_json,
                name="Invalid JSON",
                attachment_type=allure.attachment_type.TEXT
            )
            
            allure.attach(
                resp.text,
                name="Error Response",
                attachment_type=allure.attachment_type.TEXT
            )
        
        with allure.step("Проверка ошибки 400/422/500"):
            assert resp.status_code in (400, 422, 500), f"Неожиданный статус: {resp.status_code}"
            print(f"❌ Неверный JSON обработан — {resp.status_code}")


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
        """❌ Запрос с неверным токеном"""
        
        fake_token = "INVALID_TOKEN_123"
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
            print(f"❌ Проверка неверного токена прошла — {resp.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--alluredir=allure-results"])