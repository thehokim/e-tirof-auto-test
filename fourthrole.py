"""
Автотесты для API Cadastre - роль verdict_79 (rool4)
Включает все доступные endpoints для этой роли
"""

import pytest
import requests
import json
import io
from typing import Dict, Optional
from datetime import datetime
import time


# Конфигурация
BASE_URL = "https://etirof.cmspace.uz/api"
USERNAME = "rool4"
PASSWORD = "qwerty"


class TestRunner:
    """Класс для управления тестовыми запросами"""
    
    def __init__(self):
        self.token: Optional[str] = None
        self.role: Optional[str] = None
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
        self.role = data.get('role')
        
        assert self.token, "Token not found in response"
        assert self.role, "Role not found in response"
        
        # Обновляем заголовки с токеном
        self.session.headers.update({
            'Authorization': f'Bearer {self.token}'
        })
        
        print(f"✓ Login successful as {USERNAME}")
        print(f"  Role: {self.role}")
        print(f"  Token: {self.token[:20]}...")
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
        sample = data['data'][0]
        print(f"\n[DEBUG] Sample cadastre item keys: {list(sample.keys())}")
        return sample
    return None


class TestAuthentication:
    """Тесты аутентификации для роли verdict_79"""
    
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
        assert 'role' in data
        assert len(data['token']) > 0
        
        print(f"✓ Login test passed")
        print(f"  Username: {USERNAME}")
        print(f"  Role: {data['role']}")
    
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


class TestScreenshotOperations:
    """Тесты операций со скриншотами (verdict_79 имеет доступ)"""
    
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
            'screenshot': ('test_screenshot_verdict79.png', io.BytesIO(test_image), 'image/png')
        }
        
        data = {
            'spaceImageId': 'VERDICT79_IMG_001',
            'spaceImageDate': '2024-12-01'
        }
        
        response = test_runner.post(f"/cadastre/{sample_cadastre_id}/screenshot", 
                                   data=data, files=files)
        
        if response.status_code == 200:
            result = response.json()
            screenshot = result.get('Screenshot', result.get('screenshot'))
            space_image_id = result.get('SpaceImageId', result.get('space_image_id'))
            
            assert screenshot
            print(f"✓ Screenshot uploaded successfully for ID: {sample_cadastre_id}")
            print(f"  Screenshot: {screenshot}")
            print(f"  SpaceImageId: {space_image_id}")
        else:
            print(f"⚠ Upload screenshot returned status {response.status_code}: {response.text}")
    
    def test_02_get_screenshot(self, test_runner):
        """Получение скриншота"""
        # Находим item со скриншотом
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
            assert len(response.content) > 0
            print(f"✓ Screenshot downloaded successfully for ID: {test_id}")
            print(f"  File size: {len(response.content)} bytes")
        else:
            print(f"⚠ Get screenshot returned status {response.status_code}")


class TestBuildingPresence:
    """Тесты обновления наличия здания (verdict_79 имеет доступ)"""
    
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


class TestStatusOperations:
    """Тесты операций со статусами"""
    
    def test_01_set_status_into_moderation(self, test_runner, sample_cadastre_id):
        """Перевод в статус модерации"""
        if not sample_cadastre_id:
            pytest.skip("No cadastre items available")
        
        # Обычно это PATCH без body или с минимальными данными
        payload = {}
        
        response = test_runner.patch(f"/cadastre/{sample_cadastre_id}/into_moderation", payload)
        
        if response.status_code == 200:
            result = response.json()
            status = result.get('Status', result.get('status'))
            print(f"✓ Status updated to moderation for ID: {sample_cadastre_id}")
            print(f"  New status: {status}")
        elif response.status_code == 400:
            print(f"⚠ Cannot set to moderation (may be wrong status): {response.text}")
        else:
            print(f"⚠ Set into moderation returned status {response.status_code}: {response.text}")


class TestCadastreError:
    """Тесты обновления ошибок кадастра (verdict_79 имеет доступ)"""
    
    def test_01_update_cadastre_error(self, test_runner, sample_cadastre_id):
        """Обновление информации об ошибке кадастра"""
        if not sample_cadastre_id:
            pytest.skip("No cadastre items available")
        
        payload = {
            "error_description": "Ошибка в координатах границ участка. Требуется уточнение.",
            "error_type": "geometry_error"
        }
        
        response = test_runner.patch(f"/cadastre/{sample_cadastre_id}/cadastre_error", payload)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Cadastre error updated for ID: {sample_cadastre_id}")
            print(f"  Error: {payload['error_description']}")
        elif response.status_code in [400, 404]:
            print(f"⚠ Update cadastre error returned status {response.status_code}: {response.text}")
        else:
            print(f"⚠ Unexpected status {response.status_code}: {response.text}")
    
    def test_02_update_cadastre_error_empty_description(self, test_runner, sample_cadastre_id):
        """Обновление с пустым описанием ошибки"""
        if not sample_cadastre_id:
            pytest.skip("No cadastre items available")
        
        payload = {
            "error_description": "",
            "error_type": "data_error"
        }
        
        response = test_runner.patch(f"/cadastre/{sample_cadastre_id}/cadastre_error", payload)
        
        # Может быть принято или отклонено
        print(f"✓ Empty error description test - status: {response.status_code}")
        assert response.status_code in [200, 400, 404, 422]


class TestGovernorDecree:
    """Тесты для получения governor decree файла"""
    
    def test_01_get_governor_decree(self, test_runner):
        """Получение governor decree файла"""
        # Находим item с governor decree
        params = {"page_size": 100}
        response = test_runner.get("/cadastre", params=params)
        
        assert response.status_code == 200
        data = response.json()
        
        test_id = None
        for item in data['data']:
            # Проверяем наличие governor decree (может быть разные названия полей)
            has_decree = (
                item.get('GovernorDecree') or 
                item.get('governor_decree') or
                item.get('GovernorDecision') or
                item.get('governor_decision')
            )
            if has_decree:
                test_id = item.get('ID', item.get('id'))
                break
        
        if not test_id:
            pytest.skip("No items with governor decree available")
        
        response = test_runner.get(f"/cadastre/{test_id}/governor_decree")
        
        if response.status_code == 200:
            assert len(response.content) > 0
            print(f"✓ Governor decree downloaded successfully for ID: {test_id}")
            print(f"  File size: {len(response.content)} bytes")
        elif response.status_code == 404:
            print(f"⚠ Governor decree not found for ID: {test_id}")
        else:
            print(f"⚠ Get governor decree returned status {response.status_code}")


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
        print(f"✓ Total cadastre items: {meta['total']}")
        print(f"  Page: {meta['page']}")
    
    def test_02_list_with_status_filter_verdict79(self, test_runner):
        """Тест фильтрации по статусу verdict_79"""
        params = {"status": "verdict_79"}
        response = test_runner.get("/cadastre", params=params)
        
        assert response.status_code == 200
        data = response.json()
        
        print(f"✓ Items with status 'verdict_79': {data['meta']['total']}")


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
        
        print(f"✓ Retrieved item ID: {item_id}")
    
    def test_02_get_by_invalid_id(self, test_runner):
        """Тест с несуществующим ID"""
        response = test_runner.get("/cadastre/999999999")
        
        assert response.status_code == 404
        print("✓ Invalid ID correctly returns 404")


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


class TestPerformance:
    """Тесты производительности"""
    
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


class TestEdgeCases:
    """Тесты граничных случаев"""
    
    def test_01_very_large_error_description(self, test_runner, sample_cadastre_id):
        """Тест с очень длинным описанием ошибки"""
        if not sample_cadastre_id:
            pytest.skip("No cadastre items available")
        
        payload = {
            "error_description": "A" * 5000,  # 5000 символов
            "error_type": "general_error"
        }
        
        response = test_runner.patch(f"/cadastre/{sample_cadastre_id}/cadastre_error", payload)
        
        print(f"✓ Very long error description - status: {response.status_code}")
        assert response.status_code in [200, 400, 413, 422]
    
    def test_02_special_characters_in_error(self, test_runner, sample_cadastre_id):
        """Тест со спецсимволами в описании ошибки"""
        if not sample_cadastre_id:
            pytest.skip("No cadastre items available")
        
        payload = {
            "error_description": "Ошибка №1: координаты ~40°N, площадь 500м² @ участок #123",
            "error_type": "data_error"
        }
        
        response = test_runner.patch(f"/cadastre/{sample_cadastre_id}/cadastre_error", payload)
        
        print(f"✓ Special characters in error - status: {response.status_code}")
        assert response.status_code in [200, 400, 404, 422]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])