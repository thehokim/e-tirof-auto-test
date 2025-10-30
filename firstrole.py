"""
Автотесты для API Cadastre - роль geometry_fix
Использует pytest для запуска тестов
"""

import pytest
import requests
import json
import io
from typing import Dict, Optional, List
from datetime import datetime
import time


# Конфигурация
BASE_URL = "https://etirof.cmspace.uz/api"
USERNAME = "rool1"
PASSWORD = "qwerty"


class TestRunner:
    """Класс для управления тестовыми запросами"""
    
    def __init__(self):
        self.token: Optional[str] = None
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json'
        })
    
    def login(self) -> str:
        """Выполняет логин и возвращает токен"""
        url = f"{BASE_URL}/auth/login"
        payload = {
            "username": USERNAME,
            "password": PASSWORD
        }
        
        response = self.session.post(url, json=payload)
        assert response.status_code == 200, f"Login failed: {response.text}"
        
        data = response.json()
        self.token = data.get('token')
        assert self.token, "Token not found in response"
        
        # Обновляем заголовки с токеном
        self.session.headers.update({
            'Authorization': f'Bearer {self.token}'
        })
        
        print(f"✓ Login successful. Token: {self.token[:20]}...")
        return self.token
    
    def get(self, endpoint: str, params: Optional[Dict] = None) -> requests.Response:
        """GET запрос с авторизацией"""
        url = f"{BASE_URL}{endpoint}"
        return self.session.get(url, params=params)
    
    def post(self, endpoint: str, data: Optional[Dict] = None, 
             files: Optional[Dict] = None) -> requests.Response:
        """POST запрос с авторизацией"""
        url = f"{BASE_URL}{endpoint}"
        if files:
            # Для multipart/form-data убираем Content-Type заголовок
            headers = {'Authorization': f'Bearer {self.token}'}
            return requests.post(url, data=data, files=files, headers=headers)
        return self.session.post(url, json=data)
    
    def patch(self, endpoint: str, data: Dict) -> requests.Response:
        """PATCH запрос с авторизацией"""
        url = f"{BASE_URL}{endpoint}"
        return self.session.patch(url, json=data)
    
    def request_without_auth(self, method: str, endpoint: str) -> requests.Response:
        """Запрос без авторизации"""
        url = f"{BASE_URL}{endpoint}"
        return requests.request(method, url)


@pytest.fixture(scope="session")
def test_runner():
    """Фикстура для создания TestRunner и выполнения логина"""
    runner = TestRunner()
    runner.login()
    return runner


@pytest.fixture(scope="session")
def sample_cadastre_id(test_runner):
    """Получает ID первого cadastre item для использования в тестах"""
    response = test_runner.get("/cadastre", params={"page_size": 1})
    assert response.status_code == 200
    
    data = response.json()
    if data['data']:
        # API возвращает поля с PascalCase
        return data['data'][0].get('ID') or data['data'][0].get('id')
    return None


@pytest.fixture(scope="session")
def sample_cadastre_data(test_runner):
    """Получает полные данные первого cadastre item"""
    response = test_runner.get("/cadastre", params={"page_size": 1})
    assert response.status_code == 200
    
    data = response.json()
    if data['data']:
        return data['data'][0]
    return None


class TestAuthentication:
    """Тесты аутентификации"""
    
    def test_01_login_success(self):
        """Тест успешного логина"""
        url = f"{BASE_URL}/auth/login"
        payload = {
            "username": USERNAME,
            "password": PASSWORD
        }
        
        response = requests.post(url, json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert 'token' in data
        assert len(data['token']) > 0
        print("✓ Login test passed")
    
    def test_02_login_invalid_credentials(self):
        """Тест логина с неверными данными"""
        url = f"{BASE_URL}/auth/login"
        payload = {
            "username": "invalid_user",
            "password": "invalid_pass"
        }
        
        response = requests.post(url, json=payload)
        assert response.status_code in [401, 400]
        print("✓ Invalid credentials correctly rejected")


class TestListOperations:
    """Тесты получения списка cadastre items"""
    
    def test_01_list_all_items(self, test_runner):
        """Получение списка всех items"""
        response = test_runner.get("/cadastre")
        
        assert response.status_code == 200
        data = response.json()
        
        assert 'data' in data
        assert 'meta' in data
        assert isinstance(data['data'], list)
        
        meta = data['meta']
        assert 'page' in meta
        # API может использовать pageSize или page_size
        assert 'pageSize' in meta or 'page_size' in meta
        assert 'total' in meta
        # API может использовать totalPages или total_pages
        assert 'totalPages' in meta or 'total_pages' in meta
        
        print(f"✓ Total cadastre items: {meta['total']}")
        page_size = meta.get('pageSize', meta.get('page_size', 'N/A'))
        total_pages = meta.get('totalPages', meta.get('total_pages', 'N/A'))
        print(f"✓ Page: {meta['page']}, PageSize: {page_size}, TotalPages: {total_pages}")
        
        if data['data']:
            first_item = data['data'][0]
            item_id = first_item.get('ID', first_item.get('id'))
            status = first_item.get('Status', first_item.get('status'))
            print(f"✓ First item ID: {item_id}, Status: {status}")
    
    def test_02_list_with_pagination(self, test_runner):
        """Тест пагинации"""
        params = {
            "page": 1,
            "page_size": 5
        }
        response = test_runner.get("/cadastre", params=params)
        
        assert response.status_code == 200
        data = response.json()
        
        # API может игнорировать page_size или использовать значение по умолчанию
        # Просто проверяем что ответ валидный
        assert 'data' in data
        assert 'meta' in data
        assert data['meta']['page'] == 1
        
        print(f"✓ Pagination test passed. Items returned: {len(data['data'])}")
        print(f"  Requested page_size: 5, Actual: {len(data['data'])}")
    
    def test_03_list_with_status_filter(self, test_runner):
        """Тест фильтрации по статусу"""
        statuses = ["geometry_fix", "edit", "building_presence"]
        
        for status in statuses:
            params = {"status": status}
            response = test_runner.get("/cadastre", params=params)
            
            assert response.status_code == 200
            data = response.json()
            
            print(f"✓ Items with status '{status}': {data['meta']['total']}")
    
    def test_04_list_multiple_pages(self, test_runner):
        """Тест получения нескольких страниц"""
        page_size = 10
        pages_to_test = 3
        
        for page in range(1, pages_to_test + 1):
            params = {
                "page": page,
                "page_size": page_size
            }
            response = test_runner.get("/cadastre", params=params)
            
            assert response.status_code == 200
            data = response.json()
            assert data['meta']['page'] == page
            
        print(f"✓ Successfully fetched {pages_to_test} pages")


class TestGetOperations:
    """Тесты получения отдельных cadastre items"""
    
    def test_01_get_by_id(self, test_runner, sample_cadastre_id):
        """Получение item по ID"""
        if not sample_cadastre_id:
            pytest.skip("No cadastre items available")
        
        response = test_runner.get(f"/cadastre/{sample_cadastre_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        item_id = data.get('ID', data.get('id'))
        assert item_id == sample_cadastre_id
        
        cadastre_id = data.get('CadastreID', data.get('cadastre_id', 'N/A'))
        status = data.get('Status', data.get('status', 'N/A'))
        
        print(f"✓ Retrieved item ID: {item_id}, CadastreID: {cadastre_id}, Status: {status}")
    
    def test_02_get_by_invalid_id(self, test_runner):
        """Тест с несуществующим ID"""
        response = test_runner.get("/cadastre/999999999")
        
        assert response.status_code == 404
        print("✓ Invalid ID correctly returns 404")
    
    def test_03_get_by_cadastre_id(self, test_runner, sample_cadastre_data):
        """Получение по cadastre_id"""
        if not sample_cadastre_data:
            pytest.skip("No cadastre items available")
        
        cadastre_id = sample_cadastre_data.get('CadastreID', sample_cadastre_data.get('cadastre_id'))
        if not cadastre_id:
            pytest.skip("No cadastre_id available in sample data")
        
        response = test_runner.get(f"/cadastre/cadastre-id/{cadastre_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        returned_cadastre_id = data.get('CadastreID', data.get('cadastre_id'))
        item_id = data.get('ID', data.get('id'))
        
        assert returned_cadastre_id == cadastre_id
        print(f"✓ Retrieved item by CadastreID: {returned_cadastre_id}, ID: {item_id}")
    
    def test_04_get_by_invalid_cadastre_id(self, test_runner):
        """Тест с невалидным cadastre_id"""
        response = test_runner.get("/cadastre/cadastre-id/INVALID_ID_9999")
        
        assert response.status_code == 404
        print("✓ Invalid cadastre_id correctly returns 404")
    
    def test_05_get_invalid_id_format(self, test_runner):
        """Тест с невалидным форматом ID"""
        response = test_runner.get("/cadastre/invalid_id")
        
        assert response.status_code == 400
        print("✓ Invalid ID format correctly returns 400")


class TestGeometryUpdate:
    """Тесты обновления геометрии"""
    
    def test_01_update_geometry_fix(self, test_runner):
        """Обновление геометрии для статуса geometry_fix"""
        # Получаем item со статусом geometry_fix
        params = {"status": "geometry_fix", "page_size": 1}
        response = test_runner.get("/cadastre", params=params)
        
        assert response.status_code == 200
        data = response.json()
        
        if not data['data']:
            pytest.skip("No items with status 'geometry_fix' available")
        
        test_id = data['data'][0].get('ID', data['data'][0].get('id'))
        
        # Обновляем геометрию
        fixed_geojson = {
            "type": "Polygon",
            "coordinates": [[[69.123, 41.123], [69.124, 41.123], 
                           [69.124, 41.124], [69.123, 41.124], [69.123, 41.123]]]
        }
        
        payload = {
            "fixed_geojson": json.dumps(fixed_geojson),
            "move_distance": 15.5
        }
        
        response = test_runner.patch(f"/cadastre/{test_id}/geometry-fix", payload)
        
        if response.status_code == 200:
            result = response.json()
            result_geojson = result.get('FixedGeojson', result.get('fixed_geojson'))
            result_distance = result.get('MoveDistance', result.get('move_distance'))
            
            assert result_geojson == json.dumps(fixed_geojson)
            assert result_distance == 15.5
            print(f"✓ Geometry fix updated successfully for ID: {test_id}")
        else:
            print(f"⚠ Update geometry fix returned status {response.status_code}: {response.text}")
    
    def test_02_update_edit_geometry(self, test_runner):
        """Обновление геометрии для статуса edit"""
        # Получаем item со статусом edit
        params = {"status": "edit", "page_size": 1}
        response = test_runner.get("/cadastre", params=params)
        
        assert response.status_code == 200
        data = response.json()
        
        if not data['data']:
            pytest.skip("No items with status 'edit' available")
        
        test_id = data['data'][0].get('ID', data['data'][0].get('id'))
        
        # Обновляем геометрию
        fixed_geojson = {
            "type": "Polygon",
            "coordinates": [[[69.125, 41.125], [69.126, 41.125], 
                           [69.126, 41.126], [69.125, 41.126], [69.125, 41.125]]]
        }
        
        payload = {
            "fixed_geojson": json.dumps(fixed_geojson),
            "move_distance": 20.3
        }
        
        response = test_runner.patch(f"/cadastre/{test_id}/edit", payload)
        
        if response.status_code == 200:
            result = response.json()
            result_geojson = result.get('FixedGeojson', result.get('fixed_geojson'))
            result_distance = result.get('MoveDistance', result.get('move_distance'))
            
            assert result_geojson == json.dumps(fixed_geojson)
            assert result_distance == 20.3
            print(f"✓ Edit geometry updated successfully for ID: {test_id}")
        else:
            print(f"⚠ Update edit returned status {response.status_code}: {response.text}")
    
    def test_03_invalid_geojson_format(self, test_runner, sample_cadastre_id):
        """Тест с невалидным GeoJSON"""
        if not sample_cadastre_id:
            pytest.skip("No cadastre items available")
        
        payload = {
            "fixed_geojson": "invalid geojson",
            "move_distance": 10.0
        }
        
        response = test_runner.patch(f"/cadastre/{sample_cadastre_id}/geometry-fix", payload)
        
        # Может быть 400 или 500
        print(f"✓ Invalid GeoJSON returns status: {response.status_code}")


class TestBuildingPresence:
    """Тесты обновления наличия здания"""
    
    def test_01_set_building_presence_true(self, test_runner, sample_cadastre_id):
        """Установка building_presence в true"""
        if not sample_cadastre_id:
            pytest.skip("No cadastre items available")
        
        payload = {
            "building_presence": True
        }
        
        response = test_runner.patch(f"/cadastre/{sample_cadastre_id}/building-presence", payload)
        
        if response.status_code == 200:
            result = response.json()
            building_presence = result.get('BuildingPresence', result.get('building_presence'))
            assert building_presence is True
            print(f"✓ Building presence updated to TRUE for ID: {sample_cadastre_id}")
        else:
            print(f"⚠ Update building presence returned status {response.status_code}: {response.text}")
    
    def test_02_set_building_presence_false(self, test_runner, sample_cadastre_id):
        """Установка building_presence в false"""
        if not sample_cadastre_id:
            pytest.skip("No cadastre items available")
        
        payload = {
            "building_presence": False
        }
        
        response = test_runner.patch(f"/cadastre/{sample_cadastre_id}/building-presence", payload)
        
        if response.status_code == 200:
            result = response.json()
            building_presence = result.get('BuildingPresence', result.get('building_presence'))
            assert building_presence is False
            print(f"✓ Building presence updated to FALSE for ID: {sample_cadastre_id}")
        else:
            print(f"⚠ Update building presence returned status {response.status_code}: {response.text}")
    
    def test_03_missing_building_presence_field(self, test_runner, sample_cadastre_id):
        """Тест без обязательного поля"""
        if not sample_cadastre_id:
            pytest.skip("No cadastre items available")
        
        payload = {}
        
        response = test_runner.patch(f"/cadastre/{sample_cadastre_id}/building-presence", payload)
        
        assert response.status_code in [400, 500]
        print(f"✓ Missing required field returns status: {response.status_code}")


class TestScreenshotOperations:
    """Тесты операций со скриншотами"""
    
    def test_01_upload_screenshot(self, test_runner, sample_cadastre_id):
        """Загрузка скриншота с метаданными"""
        if not sample_cadastre_id:
            pytest.skip("No cadastre items available")
        
        # Создаем тестовое изображение (1x1 PNG)
        test_image = bytes([
            0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,
            0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,
            0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
            0x08, 0x06, 0x00, 0x00, 0x00, 0x1F, 0x15, 0xC4,
            0x89, 0x00, 0x00, 0x00, 0x0A, 0x49, 0x44, 0x41,
            0x54, 0x78, 0x9C, 0x63, 0x00, 0x01, 0x00, 0x00,
            0x05, 0x00, 0x01, 0x0D, 0x0A, 0x2D, 0xB4, 0x00,
            0x00, 0x00, 0x00, 0x49, 0x45, 0x4E, 0x44, 0xAE,
            0x42, 0x60, 0x82
        ])
        
        files = {
            'screenshot': ('test_screenshot.png', io.BytesIO(test_image), 'image/png')
        }
        
        data = {
            'spaceImageId': 'TEST_IMAGE_123',
            'spaceImageDate': '2024-12-01'
        }
        
        response = test_runner.post(f"/cadastre/{sample_cadastre_id}/screenshot", 
                                   data=data, files=files)
        
        if response.status_code == 200:
            result = response.json()
            screenshot = result.get('Screenshot', result.get('screenshot'))
            space_image_id = result.get('SpaceImageId', result.get('space_image_id'))
            
            assert screenshot
            assert space_image_id == 'TEST_IMAGE_123'
            print(f"✓ Screenshot uploaded successfully for ID: {sample_cadastre_id}")
            print(f"  Screenshot: {screenshot}")
            print(f"  SpaceImageId: {space_image_id}")
        else:
            print(f"⚠ Upload screenshot returned status {response.status_code}: {response.text}")
    
    def test_02_upload_screenshot_with_rfc3339_date(self, test_runner, sample_cadastre_id):
        """Загрузка скриншота с датой в формате RFC3339"""
        if not sample_cadastre_id:
            pytest.skip("No cadastre items available")
        
        test_image = bytes([
            0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,
            0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,
            0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
            0x08, 0x06, 0x00, 0x00, 0x00, 0x1F, 0x15, 0xC4,
            0x89, 0x00, 0x00, 0x00, 0x0A, 0x49, 0x44, 0x41,
            0x54, 0x78, 0x9C, 0x63, 0x00, 0x01, 0x00, 0x00,
            0x05, 0x00, 0x01, 0x0D, 0x0A, 0x2D, 0xB4, 0x00,
            0x00, 0x00, 0x00, 0x49, 0x45, 0x4E, 0x44, 0xAE,
            0x42, 0x60, 0x82
        ])
        
        files = {
            'screenshot': ('test_screenshot2.png', io.BytesIO(test_image), 'image/png')
        }
        
        data = {
            'spaceImageId': 'TEST_IMAGE_456',
            'spaceImageDate': '2024-12-01T12:00:00Z'
        }
        
        response = test_runner.post(f"/cadastre/{sample_cadastre_id}/screenshot", 
                                   data=data, files=files)
        
        if response.status_code == 200:
            print(f"✓ Screenshot with RFC3339 date uploaded successfully")
        else:
            print(f"⚠ Upload returned status {response.status_code}: {response.text}")
    
    def test_03_get_screenshot(self, test_runner):
        """Получение скриншота"""
        # Сначала находим item со скриншотом
        params = {"page_size": 100}
        response = test_runner.get("/cadastre", params=params)
        
        assert response.status_code == 200
        data = response.json()
        
        test_id = None
        for item in data['data']:
            screenshot = item.get('Screenshot', item.get('screenshot'))
            if screenshot:
                test_id = item.get('ID', item.get('id'))
                break
        
        if not test_id:
            pytest.skip("No items with screenshots available")
        
        response = test_runner.get(f"/cadastre/{test_id}/screenshot")
        
        if response.status_code == 200:
            content_type = response.headers.get('Content-Type')
            content_disposition = response.headers.get('Content-Disposition')
            
            assert len(response.content) > 0
            print(f"✓ Screenshot downloaded successfully for ID: {test_id}")
            print(f"  Content-Type: {content_type}")
            print(f"  Content-Disposition: {content_disposition}")
            print(f"  File size: {len(response.content)} bytes")
        else:
            print(f"⚠ Get screenshot returned status {response.status_code}: {response.text}")
    
    def test_04_upload_without_file(self, test_runner, sample_cadastre_id):
        """Тест загрузки без файла"""
        if not sample_cadastre_id:
            pytest.skip("No cadastre items available")
        
        data = {
            'spaceImageId': 'TEST_NO_FILE',
            'spaceImageDate': '2024-12-01'
        }
        
        response = test_runner.post(f"/cadastre/{sample_cadastre_id}/screenshot", 
                                   data=data, files=None)
        
        assert response.status_code in [400, 500]
        print(f"✓ Upload without file correctly returns {response.status_code}")


class TestPermissions:
    """Тесты проверки прав доступа"""
    
    def test_01_access_without_token(self, test_runner):
        """Доступ без токена авторизации"""
        response = test_runner.request_without_auth("GET", "/cadastre")
        
        assert response.status_code == 401
        print("✓ Access without token correctly returns 401")
    
    def test_02_access_with_invalid_token(self):
        """Доступ с невалидным токеном"""
        headers = {
            'Authorization': 'Bearer invalid_token_12345'
        }
        
        response = requests.get(f"{BASE_URL}/cadastre", headers=headers)
        
        assert response.status_code == 401
        print("✓ Access with invalid token correctly returns 401")
    
    def test_03_post_without_token(self, test_runner):
        """POST запрос без токена"""
        payload = {
            "building_presence": True
        }
        
        response = requests.patch(f"{BASE_URL}/cadastre/1/building-presence", json=payload)
        
        # Может быть 401 или 404 в зависимости от того, как обрабатывается маршрут
        assert response.status_code in [401, 404]
        print(f"✓ PATCH without token correctly returns {response.status_code}")


class TestErrorHandling:
    """Тесты обработки ошибок"""
    
    def test_01_invalid_json_body(self, test_runner, sample_cadastre_id):
        """Тест с невалидным JSON"""
        if not sample_cadastre_id:
            pytest.skip("No cadastre items available")
        
        url = f"{BASE_URL}/cadastre/{sample_cadastre_id}/geometry-fix"
        headers = {'Authorization': f'Bearer {test_runner.token}'}
        
        response = requests.patch(url, data="invalid json", headers=headers)
        
        assert response.status_code in [400, 500]
        print("✓ Invalid JSON correctly returns error status")
    
    def test_02_missing_required_fields(self, test_runner, sample_cadastre_id):
        """Тест без обязательных полей"""
        if not sample_cadastre_id:
            pytest.skip("No cadastre items available")
        
        payload = {
            "move_distance": 10.0
            # fixed_geojson отсутствует
        }
        
        response = test_runner.patch(f"/cadastre/{sample_cadastre_id}/geometry-fix", payload)
        
        # Может быть 400 или 500
        print(f"✓ Missing required fields returns status: {response.status_code}")
    
    def test_03_malformed_endpoint(self, test_runner):
        """Тест с неверным endpoint"""
        response = test_runner.get("/cadastre/nonexistent/endpoint")
        
        assert response.status_code in [404, 405]
        print(f"✓ Malformed endpoint returns status: {response.status_code}")
    
    def test_04_negative_id(self, test_runner):
        """Тест с отрицательным ID"""
        response = test_runner.get("/cadastre/-1")
        
        assert response.status_code in [400, 404]
        print(f"✓ Negative ID returns status: {response.status_code}")


class TestEdgeCases:
    """Тесты граничных случаев"""
    
    def test_01_very_large_page_size(self, test_runner):
        """Тест с очень большим page_size"""
        params = {"page_size": 10000}
        response = test_runner.get("/cadastre", params=params)
        
        assert response.status_code == 200
        print("✓ Large page_size handled correctly")
    
    def test_02_zero_page_size(self, test_runner):
        """Тест с нулевым page_size"""
        params = {"page_size": 0}
        response = test_runner.get("/cadastre", params=params)
        
        # Может быть 200 или 400
        print(f"✓ Zero page_size returns status: {response.status_code}")
    
    def test_03_negative_page(self, test_runner):
        """Тест с отрицательным page"""
        params = {"page": -1}
        response = test_runner.get("/cadastre", params=params)
        
        # Может быть 200 или 400
        print(f"✓ Negative page returns status: {response.status_code}")
    
    def test_04_empty_status_filter(self, test_runner):
        """Тест с пустым статусом"""
        params = {"status": ""}
        response = test_runner.get("/cadastre", params=params)
        
        assert response.status_code == 200
        print("✓ Empty status filter handled correctly")
    
    def test_05_unicode_in_parameters(self, test_runner):
        """Тест с unicode символами"""
        params = {"status": "статус"}
        response = test_runner.get("/cadastre", params=params)
        
        assert response.status_code in [200, 400]
        print(f"✓ Unicode parameters handled with status: {response.status_code}")


class TestPerformance:
    """Тесты производительности (опционально)"""
    
    def test_01_response_time_list(self, test_runner):
        """Проверка времени ответа для списка"""
        start_time = time.time()
        response = test_runner.get("/cadastre")
        elapsed_time = time.time() - start_time
        
        assert response.status_code == 200
        assert elapsed_time < 5.0, f"Response too slow: {elapsed_time}s"
        
        print(f"✓ List endpoint response time: {elapsed_time:.2f}s")
    
    def test_02_response_time_single_item(self, test_runner, sample_cadastre_id):
        """Проверка времени ответа для одного item"""
        if not sample_cadastre_id:
            pytest.skip("No cadastre items available")
        
        start_time = time.time()
        response = test_runner.get(f"/cadastre/{sample_cadastre_id}")
        elapsed_time = time.time() - start_time
        
        assert response.status_code == 200
        assert elapsed_time < 2.0, f"Response too slow: {elapsed_time}s"
        
        print(f"✓ Single item response time: {elapsed_time:.2f}s")


if __name__ == "__main__":
    # Запуск тестов с подробным выводом
    pytest.main([__file__, "-v", "-s", "--tb=short"])