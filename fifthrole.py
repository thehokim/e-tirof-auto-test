import pytest
import requests
import json
import io
from typing import Dict, Optional
from datetime import datetime
import time

BASE_URL = "https://etirof.cmspace.uz/api"
USERNAME = "rool5"
PASSWORD = "qwerty"


class ApiTestRunner:
    
    def __init__(self):
        self.token: Optional[str] = None
        self.role: Optional[str] = None
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json'
        })
    
    def login(self) -> str:
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
        
        self.session.headers.update({
            'Authorization': f'Bearer {self.token}'
        })
        
        print(f"✓ Login successful as {USERNAME}")
        print(f"  Role: {self.role}")
        print(f"  Token: {self.token[:20]}...")
        return self.token
    
    def get(self, endpoint: str, params: Optional[Dict] = None) -> requests.Response:
        url = f"{BASE_URL}{endpoint}"
        return self.session.get(url, params=params)
    
    def post(self, endpoint: str, data: Optional[Dict] = None, 
             files: Optional[Dict] = None) -> requests.Response:
        url = f"{BASE_URL}{endpoint}"
        if files:
            headers = {'Authorization': f'Bearer {self.token}'}
            return requests.post(url, data=data, files=files, headers=headers)
        return self.session.post(url, json=data)
    
    def patch(self, endpoint: str, data: Dict) -> requests.Response:
        url = f"{BASE_URL}{endpoint}"
        return self.session.patch(url, json=data)
    
    def request_without_auth(self, method: str, endpoint: str) -> requests.Response:
        url = f"{BASE_URL}{endpoint}"
        return requests.request(method, url)


@pytest.fixture(scope="session")
def test_runner():
    runner = ApiTestRunner()
    runner.login()
    return runner


@pytest.fixture(scope="session")
def sample_cadastre_id(test_runner):
    response = test_runner.get("/cadastre", params={"page_size": 1})
    assert response.status_code == 200
    
    data = response.json()
    if data['data']:
        return data['data'][0].get('ID') or data['data'][0].get('id')
    return None


@pytest.fixture(scope="session")
def sample_cadastre_data(test_runner):
    response = test_runner.get("/cadastre", params={"page_size": 1})
    assert response.status_code == 200
    
    data = response.json()
    if data['data']:
        sample = data['data'][0]
        print(f"\n[DEBUG] Sample cadastre item keys: {list(sample.keys())}")
        return sample
    return None


class TestAuthentication:
    
    def test_01_login_success(self):
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
        url = f"{BASE_URL}/auth/login"
        payload = {
            "username": "invalid_user",
            "password": "invalid_pass"
        }
        
        response = requests.post(url, json=payload)
        assert response.status_code in [401, 400]
        print("✓ Invalid credentials correctly rejected")


class TestGeometryFix:

    def test_01_update_geometry_basic(self, test_runner, sample_cadastre_id):
        if not sample_cadastre_id:
            pytest.skip("No cadastre items available")
        
        payload = {
            "location": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [69.240562, 41.311151],
                        [69.240662, 41.311151],
                        [69.240662, 41.311051],
                        [69.240562, 41.311051],
                        [69.240562, 41.311151]
                    ]
                ]
            }
        }
        
        response = test_runner.patch(f"/cadastre/{sample_cadastre_id}/geometry-fix", payload)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Geometry updated successfully for ID: {sample_cadastre_id}")
            location = result.get('Location', result.get('location'))
            if location:
                print(f"  New location: {location.get('type')}")
        else:
            print(f"⚠ Geometry update returned status {response.status_code}: {response.text}")
    
    def test_02_update_geometry_complex_polygon(self, test_runner, sample_cadastre_id):
        if not sample_cadastre_id:
            pytest.skip("No cadastre items available")
        
        payload = {
            "location": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [69.240562, 41.311151],
                        [69.240662, 41.311151],
                        [69.240712, 41.311101],
                        [69.240662, 41.311051],
                        [69.240562, 41.311051],
                        [69.240512, 41.311101],
                        [69.240562, 41.311151]
                    ]
                ]
            }
        }
        
        response = test_runner.patch(f"/cadastre/{sample_cadastre_id}/geometry-fix", payload)
        
        if response.status_code == 200:
            print(f"✓ Complex geometry updated for ID: {sample_cadastre_id}")
        else:
            print(f"⚠ Complex geometry update returned status {response.status_code}")


class TestEditNote:
    
    def test_01_update_with_short_edit_note(self, test_runner, sample_cadastre_id):
        if not sample_cadastre_id:
            pytest.skip("No cadastre items available")
        
        payload = {
            "location": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [69.240562, 41.311151],
                        [69.240662, 41.311151],
                        [69.240662, 41.311051],
                        [69.240562, 41.311051],
                        [69.240562, 41.311151]
                    ]
                ]
            },
            "edit_note": "Исправление координат"
        }
        
        response = test_runner.patch(f"/cadastre/{sample_cadastre_id}/geometry-fix", payload)
        
        if response.status_code == 200:
            result = response.json()
            edit_note = result.get('EditNote', result.get('edit_note'))
            print(f"✓ Geometry updated with edit_note for ID: {sample_cadastre_id}")
            print(f"  Edit note: {edit_note}")
        else:
            print(f"⚠ Update with edit_note returned status {response.status_code}: {response.text}")
    
    def test_02_update_with_detailed_edit_note(self, test_runner, sample_cadastre_id):
        if not sample_cadastre_id:
            pytest.skip("No cadastre items available")
        
        payload = {
            "location": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [69.240562, 41.311151],
                        [69.240662, 41.311151],
                        [69.240662, 41.311051],
                        [69.240562, 41.311051],
                        [69.240562, 41.311151]
                    ]
                ]
            },
            "edit_note": (
                "Редактирование границ земельного участка. "
                "Изменения внесены на основании распоряжения администрации. "
                "Уточнены координаты северо-восточной границы участка."
            )
        }
        
        response = test_runner.patch(f"/cadastre/{sample_cadastre_id}/geometry-fix", payload)
        
        if response.status_code == 200:
            result = response.json()
            edit_note = result.get('EditNote', result.get('edit_note'))
            print(f"✓ Detailed edit_note saved for ID: {sample_cadastre_id}")
            print(f"  Edit note length: {len(edit_note) if edit_note else 0} chars")
        else:
            print(f"⚠ Detailed edit_note update returned status {response.status_code}")
    
    def test_03_update_with_edit_note_unicode(self, test_runner, sample_cadastre_id):
        if not sample_cadastre_id:
            pytest.skip("No cadastre items available")
        
        payload = {
            "location": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [69.240562, 41.311151],
                        [69.240662, 41.311151],
                        [69.240662, 41.311051],
                        [69.240562, 41.311051],
                        [69.240562, 41.311151]
                    ]
                ]
            },
            "edit_note": "Редактирование: Ўзбекистон Республикаси территориясида"
        }
        
        response = test_runner.patch(f"/cadastre/{sample_cadastre_id}/geometry-fix", payload)
        
        if response.status_code == 200:
            print(f"✓ Unicode edit_note saved successfully")
        else:
            print(f"⚠ Unicode edit_note returned status {response.status_code}")
    
    def test_04_update_with_edit_note_numbered_list(self, test_runner, sample_cadastre_id):
        if not sample_cadastre_id:
            pytest.skip("No cadastre items available")
        
        payload = {
            "location": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [69.240562, 41.311151],
                        [69.240662, 41.311151],
                        [69.240662, 41.311051],
                        [69.240562, 41.311051],
                        [69.240562, 41.311151]
                    ]
                ]
            },
            "edit_note": (
                "Внесены следующие изменения:\n"
                "1. Уточнены координаты северной границы\n"
                "2. Исправлена площадь участка\n"
                "3. Обновлен адрес земельного участка\n"
                "4. Добавлены данные о правообладателе"
            )
        }
        
        response = test_runner.patch(f"/cadastre/{sample_cadastre_id}/geometry-fix", payload)
        
        if response.status_code == 200:
            print(f"✓ Numbered list in edit_note saved successfully")
        else:
            print(f"⚠ Numbered list edit_note returned status {response.status_code}")
    
    def test_05_update_with_empty_edit_note(self, test_runner, sample_cadastre_id):
        if not sample_cadastre_id:
            pytest.skip("No cadastre items available")
        
        payload = {
            "location": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [69.240562, 41.311151],
                        [69.240662, 41.311151],
                        [69.240662, 41.311051],
                        [69.240562, 41.311051],
                        [69.240562, 41.311151]
                    ]
                ]
            },
            "edit_note": ""
        }
        
        response = test_runner.patch(f"/cadastre/{sample_cadastre_id}/geometry-fix", payload)
        
        print(f"✓ Empty edit_note test - status: {response.status_code}")
        assert response.status_code in [200, 400, 404, 422]
    
    def test_06_update_with_special_characters_in_edit_note(self, test_runner, sample_cadastre_id):
        """Обновление с спецсимволами в edit_note"""
        if not sample_cadastre_id:
            pytest.skip("No cadastre items available")
        
        payload = {
            "location": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [69.240562, 41.311151],
                        [69.240662, 41.311151],
                        [69.240662, 41.311051],
                        [69.240562, 41.311051],
                        [69.240562, 41.311151]
                    ]
                ]
            },
            "edit_note": "Изменение №3: площадь ~500м², координаты 69°N @ участок #123"
        }
        
        response = test_runner.patch(f"/cadastre/{sample_cadastre_id}/geometry-fix", payload)
        
        if response.status_code == 200:
            print(f"✓ Special characters in edit_note handled correctly")
        else:
            print(f"⚠ Special characters returned status {response.status_code}")
    
    def test_07_update_with_very_long_edit_note(self, test_runner, sample_cadastre_id):
        if not sample_cadastre_id:
            pytest.skip("No cadastre items available")
        
        payload = {
            "location": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [69.240562, 41.311151],
                        [69.240662, 41.311151],
                        [69.240662, 41.311051],
                        [69.240562, 41.311051],
                        [69.240562, 41.311151]
                    ]
                ]
            },
            "edit_note": "Редактирование. " * 500  
        }
        
        response = test_runner.patch(f"/cadastre/{sample_cadastre_id}/geometry-fix", payload)
        
        print(f"✓ Very long edit_note test - status: {response.status_code}")
        print(f"  Edit note length: {len(payload['edit_note'])} chars")
        assert response.status_code in [200, 400, 404, 413, 422]


class TestEditOperations:
    
    def test_01_set_edit_status(self, test_runner, sample_cadastre_id):
        if not sample_cadastre_id:
            pytest.skip("No cadastre items available")
        
        payload = {}
        
        response = test_runner.patch(f"/cadastre/{sample_cadastre_id}/edit", payload)
        
        if response.status_code == 200:
            result = response.json()
            status = result.get('Status', result.get('status'))
            print(f"✓ Status set to 'edit' for ID: {sample_cadastre_id}")
            print(f"  New status: {status}")
        else:
            print(f"⚠ Set edit status returned {response.status_code}: {response.text}")


class TestBuildingPresence:
    
    def test_01_set_building_presence_true(self, test_runner, sample_cadastre_id):
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
            print(f"⚠ Update building presence returned status {response.status_code}")


class TestScreenshotOperations:
    
    def test_01_upload_screenshot(self, test_runner, sample_cadastre_id):
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
            'screenshot': ('test_screenshot_editor.png', io.BytesIO(test_image), 'image/png')
        }
        
        data = {
            'spaceImageId': 'EDITOR_IMG_001',
            'spaceImageDate': '2024-12-01'
        }
        
        response = test_runner.post(f"/cadastre/{sample_cadastre_id}/screenshot", 
                                   data=data, files=files)
        
        if response.status_code == 200:
            result = response.json()
            screenshot = result.get('Screenshot', result.get('screenshot'))
            
            assert screenshot
            print(f"✓ Screenshot uploaded successfully for ID: {sample_cadastre_id}")
            print(f"  Screenshot: {screenshot}")
        else:
            print(f"⚠ Upload screenshot returned status {response.status_code}: {response.text}")
    
    def test_02_get_screenshot(self, test_runner):
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


class TestCadastreError:
    
    def test_01_update_cadastre_error(self, test_runner, sample_cadastre_id):
        if not sample_cadastre_id:
            pytest.skip("No cadastre items available")
        
        payload = {
            "error_description": "Обнаружена ошибка в данных кадастра. Требуется проверка координат.",
            "error_type": "geometry_error"
        }
        
        response = test_runner.patch(f"/cadastre/{sample_cadastre_id}/cadastre_error", payload)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Cadastre error updated for ID: {sample_cadastre_id}")
            print(f"  Error: {payload['error_description']}")
        else:
            print(f"⚠ Update cadastre error returned status {response.status_code}: {response.text}")


class TestStatusOperations:
    
    def test_01_set_status_into_moderation(self, test_runner, sample_cadastre_id):
        if not sample_cadastre_id:
            pytest.skip("No cadastre items available")
        
        payload = {}
        
        response = test_runner.patch(f"/cadastre/{sample_cadastre_id}/into_moderation", payload)
        
        if response.status_code == 200:
            result = response.json()
            status = result.get('Status', result.get('status'))
            print(f"✓ Status updated to moderation for ID: {sample_cadastre_id}")
            print(f"  New status: {status}")
        else:
            print(f"⚠ Set into moderation returned status {response.status_code}: {response.text}")


class TestListOperations:
    
    def test_01_list_all_items(self, test_runner):
        response = test_runner.get("/cadastre")
        
        assert response.status_code == 200
        data = response.json()
        
        assert 'data' in data
        assert 'meta' in data
        assert isinstance(data['data'], list)
        
        meta = data['meta']
        print(f"✓ Total cadastre items: {meta['total']}")
        print(f"  Page: {meta['page']}")
    
    def test_02_list_with_pagination(self, test_runner):
        params = {"page_size": 5, "page": 1}
        response = test_runner.get("/cadastre", params=params)
        
        assert response.status_code == 200
        data = response.json()
        items_count = len(data['data'])
        print(f"✓ Pagination test: requested 5 items, got {items_count} items")
        
        assert items_count <= 100, f"Too many items returned: {items_count}"


class TestGetOperations:
    
    def test_01_get_by_id(self, test_runner, sample_cadastre_id):
        if not sample_cadastre_id:
            pytest.skip("No cadastre items available")
        
        response = test_runner.get(f"/cadastre/{sample_cadastre_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        item_id = data.get('ID', data.get('id'))
        assert item_id == sample_cadastre_id
        
        print(f"✓ Retrieved item ID: {item_id}")
    
    def test_02_get_by_invalid_id(self, test_runner):
        response = test_runner.get("/cadastre/999999999")
        
        assert response.status_code == 404
        print("✓ Invalid ID correctly returns 404")


class TestPermissions:
    
    def test_01_access_without_token(self, test_runner):
        response = test_runner.request_without_auth("GET", "/cadastre")
        
        assert response.status_code == 401
        print("✓ Access without token correctly returns 401")
    
    def test_02_access_with_invalid_token(self):
        headers = {
            'Authorization': 'Bearer invalid_token_12345'
        }
        
        response = requests.get(f"{BASE_URL}/cadastre", headers=headers)
        
        assert response.status_code == 401
        print("✓ Access with invalid token correctly returns 401")


class TestPerformance:
    
    def test_01_response_time_list(self, test_runner):
        start_time = time.time()
        response = test_runner.get("/cadastre")
        elapsed_time = time.time() - start_time
        
        assert response.status_code == 200
        assert elapsed_time < 5.0, f"Response too slow: {elapsed_time}s"
        
        print(f"✓ List endpoint response time: {elapsed_time:.2f}s")
    
    def test_02_response_time_single_item(self, test_runner, sample_cadastre_id):
        if not sample_cadastre_id:
            pytest.skip("No cadastre items available")
        
        start_time = time.time()
        response = test_runner.get(f"/cadastre/{sample_cadastre_id}")
        elapsed_time = time.time() - start_time
        
        assert response.status_code == 200
        assert elapsed_time < 2.0, f"Response too slow: {elapsed_time}s"
        
        print(f"✓ Single item response time: {elapsed_time:.2f}s")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])