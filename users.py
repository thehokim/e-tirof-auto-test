import pytest
import requests
import random
import string
from typing import Dict, Optional
import time


BASE_URL = "https://etirof.cmspace.uz/api"
USERS_ENDPOINT = f"{BASE_URL}/users"


class UserApiClient:
    """Класс для работы с User Management API"""
    
    def __init__(self, token: str):
        self.token = token
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        })
    
    def create_user(self, payload: Dict) -> requests.Response:
        """Создание пользователя"""
        return self.session.post(USERS_ENDPOINT, json=payload)
    
    def get_user(self, user_id: int) -> requests.Response:
        """Получение пользователя по ID"""
        return self.session.get(f"{USERS_ENDPOINT}/{user_id}")
    
    def update_user(self, user_id: int, payload: Dict) -> requests.Response:
        """Обновление пользователя"""
        return self.session.put(f"{USERS_ENDPOINT}/{user_id}", json=payload)
    
    def delete_user(self, user_id: int) -> requests.Response:
        """Удаление пользователя"""
        return self.session.delete(f"{USERS_ENDPOINT}/{user_id}")
    
    def toggle_active(self, user_id: int) -> requests.Response:
        """Переключение статуса active"""
        return self.session.patch(f"{USERS_ENDPOINT}/{user_id}/toggle-active")
    
    def list_users(self, params: Optional[Dict] = None) -> requests.Response:
        """Получение списка пользователей"""
        return self.session.get(USERS_ENDPOINT, params=params)


def random_username(prefix: str = "testuser") -> str:
    """Генерация случайного username"""
    return f"{prefix}_{''.join(random.choices(string.ascii_lowercase, k=6))}"


def random_password() -> str:
    """Генерация случайного пароля"""
    return ''.join(random.choices(string.ascii_letters + string.digits + "@#$%", k=12))


@pytest.fixture(scope="session")
def root_token():
    """Получение токена root пользователя"""
    auth_url = f"{BASE_URL}/auth/login"
    creds = {"username": "root", "password": "root"}
    
    print("\n[Setup] Logging in as root...")
    resp = requests.post(auth_url, json=creds)
    
    assert resp.status_code == 200, f"Root login failed: {resp.text}"
    
    data = resp.json()
    token = data.get("token")
    role = data.get("role")
    
    assert token, "Token not found in response"
    
    print(f"✓ Root login successful")
    print(f"  Role: {role}")
    print(f"  Token: {token[:20]}...")
    
    return token


@pytest.fixture(scope="session")
def api_client(root_token):
    """API клиент с авторизацией root"""
    return UserApiClient(root_token)


@pytest.fixture
def headers(root_token):
    """HTTP заголовки с авторизацией"""
    return {
        "Authorization": f"Bearer {root_token}",
        "Content-Type": "application/json"
    }


@pytest.fixture
def test_user_payload():
    """Базовый payload для создания пользователя"""
    return {
        "username": random_username(),
        "password": "Test123@",
        "firstName": "Auto",
        "middleName": "QA",
        "lastName": "Bot",
        "position": "tester",
        "active": True,
        "role": "cadastre_integration",
        "randomizerIndex": 1
    }


@pytest.fixture
def created_user(api_client, test_user_payload):
    """Создание тестового пользователя с автоматической очисткой"""
    print(f"\n[Setup] Creating test user: {test_user_payload['username']}")
    
    resp = api_client.create_user(test_user_payload)
    assert resp.status_code == 201, f"User creation failed: {resp.text}"
    
    user = resp.json().get("user")
    assert user, "User not found in response"
    
    print(f"✓ Test user created: ID={user['ID']}, username={user['username']}")
    
    yield user
    
    print(f"\n[Teardown] Deleting test user: ID={user['ID']}")
    delete_resp = api_client.delete_user(user['ID'])
    
    if delete_resp.status_code == 200:
        print(f"✓ Test user deleted: ID={user['ID']}")
    else:
        print(f"⚠ Failed to delete test user: {delete_resp.status_code}")


class TestUserCreation:
    """Тесты создания пользователей"""
    
    def test_01_create_user_basic(self, api_client, test_user_payload):
        """Базовое создание пользователя"""
        resp = api_client.create_user(test_user_payload)
        
        assert resp.status_code == 201
        data = resp.json()
        
        assert "user" in data
        user = data["user"]
        
        assert user["username"] == test_user_payload["username"]
        assert user["firstName"] == test_user_payload["firstName"]
        assert user["lastName"] == test_user_payload["lastName"]
        assert user["role"] == test_user_payload["role"]
        assert user["active"] is True
        assert "ID" in user
        
        print(f"✓ User created successfully: {user['username']} (ID: {user['ID']})")
        
        api_client.delete_user(user["ID"])
    
    def test_02_create_user_all_roles(self, api_client):
        """Создание пользователей с различными ролями"""
        roles = [
            "geometry_fix",
            "editor",
            "verdict_79",
            "cadastre_integration",
            "verify",
            "admin"
        ]
        
        created_users = []
        
        for role in roles:
            payload = {
                "username": random_username(f"role_{role}"),
                "password": "Test123@",
                "firstName": role.title(),
                "lastName": "Test",
                "position": f"{role}_tester",
                "active": True,
                "role": role,
                "randomizerIndex": 1
            }
            
            resp = api_client.create_user(payload)
            
            if resp.status_code == 201:
                user = resp.json()["user"]
                created_users.append(user["ID"])
                assert user["role"] == role
                print(f"✓ Created user with role '{role}': ID={user['ID']}")
            else:
                print(f"⚠ Failed to create user with role '{role}': {resp.status_code}")
        
        for user_id in created_users:
            api_client.delete_user(user_id)
        
        assert len(created_users) > 0, "No users were created"
    
    def test_03_create_user_inactive(self, api_client):
        """Создание неактивного пользователя"""
        payload = {
            "username": random_username("inactive"),
            "password": "Test123@",
            "firstName": "Inactive",
            "lastName": "User",
            "position": "tester",
            "active": False,  
            "role": "geometry_fix",
            "randomizerIndex": 1
        }
        
        resp = api_client.create_user(payload)
        
        assert resp.status_code == 201
        user = resp.json()["user"]
        
        assert user["active"] is False
        print(f"✓ Inactive user created: {user['username']}")
        
        api_client.delete_user(user["ID"])
    
    def test_04_create_user_duplicate_username(self, api_client, created_user):
        """Попытка создания пользователя с существующим username"""
        payload = {
            "username": created_user["username"],  
            "password": "Test123@",
            "firstName": "Duplicate",
            "lastName": "User",
            "position": "tester",
            "active": True,
            "role": "geometry_fix",
            "randomizerIndex": 1
        }
        
        resp = api_client.create_user(payload)
        
        assert resp.status_code in [400, 409, 422]  
        print(f"✓ Duplicate username correctly rejected: {resp.status_code}")
    
    def test_05_create_user_invalid_role(self, api_client):
        """Создание пользователя с невалидной ролью"""
        payload = {
            "username": random_username(),
            "password": "Test123@",
            "firstName": "Invalid",
            "lastName": "Role",
            "position": "tester",
            "active": True,
            "role": "invalid_role_xyz",  
            "randomizerIndex": 1
        }
        
        resp = api_client.create_user(payload)
        
        assert resp.status_code in [400, 422]
        print(f"✓ Invalid role correctly rejected: {resp.status_code}")
    
    def test_06_create_user_missing_required_fields(self, api_client):
        """Создание пользователя без обязательных полей"""
        payload = {
            "username": random_username(),
            "firstName": "Missing",
            "lastName": "Fields"
        }
        
        resp = api_client.create_user(payload)
        
        assert resp.status_code in [400, 422]
        print(f"✓ Missing required fields correctly rejected: {resp.status_code}")


class TestUserRetrieval:
    """Тесты получения пользователей"""
    
    def test_01_get_user_by_id(self, api_client, created_user):
        """Получение пользователя по ID"""
        user_id = created_user["ID"]
        
        resp = api_client.get_user(user_id)
        
        assert resp.status_code == 200
        data = resp.json()
        
        assert data["ID"] == user_id
        assert data["username"] == created_user["username"]
        
        print(f"✓ User retrieved: {data['username']} (ID: {user_id})")
    
    def test_02_get_user_nonexistent_id(self, api_client):
        """Получение несуществующего пользователя"""
        resp = api_client.get_user(999999999)
        
        assert resp.status_code == 404
        print("✓ Nonexistent user correctly returns 404")
    
    def test_03_list_all_users(self, api_client):
        """Получение списка всех пользователей"""
        resp = api_client.list_users()
        
        assert resp.status_code == 200
        data = resp.json()
        
        assert "data" in data
        assert isinstance(data["data"], list)
        assert len(data["data"]) > 0
        
        print(f"✓ Total users: {len(data['data'])}")
        
        if data["data"]:
            first_user = data["data"][0]
            assert "ID" in first_user
            assert "username" in first_user
            assert "role" in first_user
    
    def test_04_list_users_with_pagination(self, api_client):
        """Тест пагинации списка пользователей"""
        params = {"page": 1, "page_size": 5}
        
        resp = api_client.list_users(params)
        
        assert resp.status_code == 200
        data = resp.json()
        
        assert "data" in data
        assert len(data["data"]) <= 100
        
        print(f"✓ Pagination test: got {len(data['data'])} users")
    
    def test_05_list_users_filter_by_role(self, api_client):
        """Фильтрация пользователей по роли"""
        params = {"role": "geometry_fix"}
        
        resp = api_client.list_users(params)
        
        assert resp.status_code == 200
        data = resp.json()
        
        if data["data"]:
            for user in data["data"]:
                if "role" in user:
                    print(f"  User: {user['username']}, Role: {user['role']}")
        
        print(f"✓ Role filter test: found {len(data['data'])} users")


class TestUserUpdate:
    """Тесты обновления пользователей"""
    
    def test_01_update_user_firstname(self, api_client, created_user):
        """Обновление имени пользователя"""
        user_id = created_user["ID"]
        new_name = "UpdatedFirstName"
        
        payload = {"firstName": new_name}
        resp = api_client.update_user(user_id, payload)
        
        assert resp.status_code == 200
        data = resp.json()
        
        assert data["firstName"] == new_name
        print(f"✓ First name updated: {new_name}")
    
    def test_02_update_user_multiple_fields(self, api_client, created_user):
        """Обновление нескольких полей"""
        user_id = created_user["ID"]
        
        payload = {
            "firstName": "NewFirst",
            "middleName": "NewMiddle",
            "lastName": "NewLast",
            "position": "senior_tester"
        }
        
        resp = api_client.update_user(user_id, payload)
        
        assert resp.status_code == 200
        data = resp.json()
        
        assert data["firstName"] == payload["firstName"]
        assert data["middleName"] == payload["middleName"]
        assert data["lastName"] == payload["lastName"]
        assert data["position"] == payload["position"]
        
        print(f"✓ Multiple fields updated successfully")
    
    def test_03_update_user_role(self, api_client, created_user):
        """Обновление роли пользователя"""
        user_id = created_user["ID"]
        new_role = "editor"
        
        payload = {"role": new_role}
        resp = api_client.update_user(user_id, payload)
        
        if resp.status_code == 200:
            data = resp.json()
            assert data["role"] == new_role
            print(f"✓ Role updated to: {new_role}")
        else:
            print(f"⚠ Role update returned: {resp.status_code}")
            assert resp.status_code in [200, 400, 403]
    
    def test_04_update_user_password(self, api_client, created_user):
        """Обновление пароля пользователя"""
        user_id = created_user["ID"]
        new_password = "NewPassword123@"
        
        payload = {"password": new_password}
        resp = api_client.update_user(user_id, payload)
        
        assert resp.status_code in [200, 400] 
        print(f"✓ Password update request processed: {resp.status_code}")
    
    def test_05_update_nonexistent_user(self, api_client):
        """Обновление несуществующего пользователя"""
        payload = {"firstName": "Test"}
        
        resp = api_client.update_user(999999999, payload)
        
        assert resp.status_code == 404
        print("✓ Update nonexistent user correctly returns 404")


class TestUserStatusToggle:
    """Тесты переключения статуса пользователя"""
    
    def test_01_toggle_active_status(self, api_client, created_user):
        """Переключение статуса active"""
        user_id = created_user["ID"]
        initial_status = created_user["active"]
        
        resp = api_client.toggle_active(user_id)
        
        assert resp.status_code == 200
        data = resp.json()
        
        new_status = data["active"]
        assert isinstance(new_status, bool)
        assert new_status != initial_status
        
        print(f"✓ Status toggled: {initial_status} → {new_status}")
    
    def test_02_toggle_twice(self, api_client, created_user):
        """Двойное переключение статуса (должен вернуться к исходному)"""
        user_id = created_user["ID"]
        initial_status = created_user["active"]
        
        resp1 = api_client.toggle_active(user_id)
        assert resp1.status_code == 200
        status_after_first = resp1.json()["active"]
        
        resp2 = api_client.toggle_active(user_id)
        assert resp2.status_code == 200
        status_after_second = resp2.json()["active"]
        
        assert status_after_second == initial_status
        print(f"✓ Double toggle test passed: {initial_status} → {status_after_first} → {status_after_second}")
    
    def test_03_toggle_nonexistent_user(self, api_client):
        """Переключение статуса несуществующего пользователя"""
        resp = api_client.toggle_active(999999999)
        
        assert resp.status_code == 404
        print("✓ Toggle nonexistent user correctly returns 404")


class TestUserDeletion:
    """Тесты удаления пользователей"""
    
    def test_01_delete_user(self, api_client, test_user_payload):
        """Удаление пользователя"""
        create_resp = api_client.create_user(test_user_payload)
        assert create_resp.status_code == 201
        user = create_resp.json()["user"]
        user_id = user["ID"]
        
        delete_resp = api_client.delete_user(user_id)
        
        assert delete_resp.status_code == 200
        print(f"✓ User deleted: ID={user_id}")
        
        get_resp = api_client.get_user(user_id)
        assert get_resp.status_code == 404
        print(f"✓ Confirmed user is deleted")
    
    def test_02_delete_nonexistent_user(self, api_client):
        """Удаление несуществующего пользователя"""
        resp = api_client.delete_user(999999999)
        
        assert resp.status_code in [404, 200]  
        print(f"✓ Delete nonexistent user: {resp.status_code}")
    
    def test_03_delete_then_recreate(self, api_client, test_user_payload):
        """Удаление и повторное создание пользователя с тем же username"""
        create_resp1 = api_client.create_user(test_user_payload)
        assert create_resp1.status_code == 201
        user1 = create_resp1.json()["user"]
        
        delete_resp = api_client.delete_user(user1["ID"])
        assert delete_resp.status_code == 200
        
        time.sleep(0.5)
        
        create_resp2 = api_client.create_user(test_user_payload)
        
        if create_resp2.status_code == 201:
            user2 = create_resp2.json()["user"]
            print(f"✓ User recreated with same username: {user2['username']}")
            api_client.delete_user(user2["ID"])
        else:
            print(f"⚠ Recreate failed: {create_resp2.status_code}")
            assert create_resp2.status_code in [201, 400, 409]


class TestUserPermissions:
    """Тесты прав доступа"""
    
    def test_01_access_without_token(self):
        """Доступ без токена авторизации"""
        resp = requests.get(USERS_ENDPOINT)
        
        assert resp.status_code == 401
        print("✓ Access without token correctly returns 401")
    
    def test_02_access_with_invalid_token(self):
        """Доступ с невалидным токеном"""
        headers = {
            "Authorization": "Bearer invalid_token_12345",
            "Content-Type": "application/json"
        }
        
        resp = requests.get(USERS_ENDPOINT, headers=headers)
        
        assert resp.status_code == 401
        print("✓ Access with invalid token correctly returns 401")
    
    def test_03_non_root_user_cannot_create_users(self, api_client):
        """Не-root пользователь не может создавать пользователей"""
        auth_resp = requests.post(
            f"{BASE_URL}/auth/login",
            json={"username": "rool1", "password": "qwerty"}
        )
        
        if auth_resp.status_code == 200:
            user_token = auth_resp.json()["token"]
            
            headers = {
                "Authorization": f"Bearer {user_token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "username": random_username(),
                "password": "Test123@",
                "firstName": "Test",
                "lastName": "User",
                "role": "geometry_fix",
                "active": True,
                "randomizerIndex": 1
            }
            
            resp = requests.post(USERS_ENDPOINT, json=payload, headers=headers)
            
            assert resp.status_code in [403, 401]
            print(f"✓ Non-root user correctly denied access: {resp.status_code}")
        else:
            pytest.skip("Cannot login as non-root user")


class TestEdgeCases:
    """Тесты граничных случаев"""
    
    def test_01_create_user_very_long_username(self, api_client):
        """Создание пользователя с очень длинным username"""
        payload = {
            "username": "a" * 100,  
            "password": "Test123@",
            "firstName": "Long",
            "lastName": "Username",
            "role": "geometry_fix",
            "active": True,
            "randomizerIndex": 1
        }
        
        resp = api_client.create_user(payload)
        
        print(f"✓ Very long username test: {resp.status_code}")
        
        if resp.status_code == 201:
            user = resp.json()["user"]
            api_client.delete_user(user["ID"])
        
        assert resp.status_code in [201, 400, 422]
    
    def test_02_create_user_special_characters(self, api_client):
        """Создание пользователя со спецсимволами в полях"""
        payload = {
            "username": random_username(),
            "password": "Test123@",
            "firstName": "Иван",  
            "middleName": "测试",  
            "lastName": "O'Brien",  
            "position": "Senior QA Engineer #1",
            "role": "geometry_fix",
            "active": True,
            "randomizerIndex": 1
        }
        
        resp = api_client.create_user(payload)
        
        if resp.status_code == 201:
            user = resp.json()["user"]
            print(f"✓ Special characters accepted: {user['firstName']} {user['lastName']}")
            api_client.delete_user(user["ID"])
        else:
            print(f"⚠ Special characters rejected: {resp.status_code}")
        
        assert resp.status_code in [201, 400, 422]
    
    def test_03_update_user_to_empty_string(self, api_client, created_user):
        """Обновление поля на пустую строку"""
        user_id = created_user["ID"]
        
        payload = {"middleName": ""}
        resp = api_client.update_user(user_id, payload)
        
        print(f"✓ Empty string update test: {resp.status_code}")
        assert resp.status_code in [200, 400, 422]


class TestPerformance:
    """Тесты производительности"""
    
    def test_01_list_users_response_time(self, api_client):
        """Проверка времени ответа при получении списка"""
        start_time = time.time()
        resp = api_client.list_users()
        elapsed_time = time.time() - start_time
        
        assert resp.status_code == 200
        assert elapsed_time < 5.0, f"Response too slow: {elapsed_time}s"
        
        print(f"✓ List users response time: {elapsed_time:.2f}s")
    
    def test_02_create_user_response_time(self, api_client, test_user_payload):
        """Проверка времени создания пользователя"""
        start_time = time.time()
        resp = api_client.create_user(test_user_payload)
        elapsed_time = time.time() - start_time
        
        assert resp.status_code == 201
        assert elapsed_time < 3.0, f"Creation too slow: {elapsed_time}s"
        
        print(f"✓ Create user response time: {elapsed_time:.2f}s")
        
        if resp.status_code == 201:
            user = resp.json()["user"]
            api_client.delete_user(user["ID"])


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])