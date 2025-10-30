import pytest
import requests
import json
import os

BASE_URL = "https://etirof.cmspace.uz/api/cadastre/integration/push"
HEADERS = {"Authorization": "Basic Y2FkYXN0cmU6Y2FkNTY3QUFA"}

PDF_FILE_PATH = "/home/user/Downloads/12636_2_230FF8971C606F9DCE94288E49178A0490EBD387.pdf"


BASE_TEST_DATA = {
    "address": "test address",
    "land_fund_type_code": "10",
    "land_use_type_code": "20",
    "vid": "foo",
    "region_soato": "1726",
    "district_soato": "1726264",
    "neighborhood_soato": "1726264",
    "law_accordance_id": "1",
    "selected_at": "2024-03-06 12:00:00",
    "step_deadline": "2024-03-10 12:00:00",
    "location": {
        "type": "Polygon",
        "coordinates": [
            [
                [70.977547181, 40.742336418],
                [70.977609794, 40.742167422],
                [70.977411895, 40.74212747],
                [70.977405158, 40.742146528],
                [70.977376591, 40.742140742],
                [70.977363476, 40.742178108],
                [70.977310835, 40.742167422],
                [70.97730823, 40.742166878],
                [70.977189742, 40.742145439],
                [70.977099371, 40.742247054],
                [70.977547181, 40.742336418]
            ]
        ]
    },
    "mulk_egalari": [
        {"mulk_egasi": "A", "mulk_egasi_stir": "111"},
        {"mulk_egasi": "B", "mulk_egasi_stir": "222"},
        {"mulk_egasi": "C", "mulk_egasi_stir": "333"}
    ]
}


class TestCadastrePushIntegration:
    
    def _make_request(self, test_data):
        if not os.path.exists(PDF_FILE_PATH):
            pytest.skip(f"PDF file not found: {PDF_FILE_PATH}")
        
        with open(PDF_FILE_PATH, "rb") as file1:
            with open(PDF_FILE_PATH, "rb") as file2:
                files = [
                    ("uidSPUnit", (None, test_data["uidSPUnit"])),
                    ("cadastral_number", (None, test_data["cadastral_number"])),
                    ("address", (None, test_data["address"])),
                    ("land_fund_type_code", (None, test_data["land_fund_type_code"])),
                    ("land_use_type_code", (None, test_data["land_use_type_code"])),
                    ("vid", (None, test_data["vid"])),
                    ("region_soato", (None, test_data["region_soato"])),
                    ("district_soato", (None, test_data["district_soato"])),
                    ("neighborhood_soato", (None, test_data["neighborhood_soato"])),
                    ("law_accordance_id", (None, test_data["law_accordance_id"])),
                    ("selected_at", (None, test_data["selected_at"])),
                    ("step_deadline", (None, test_data["step_deadline"])),
                    ("location", (None, json.dumps(test_data["location"]))),
                    ("building_land_cad_plan", ("land_plan.pdf", file1, "application/pdf")),
                    ("governor_decree", ("decree.pdf", file2, "application/pdf")),
                    ("mulk_egalari", (None, json.dumps(test_data["mulk_egalari"]))),
                ]
                
                if "reupload_note" in test_data:
                    files.append(("reupload_note", (None, test_data["reupload_note"])))
                
                if "edit_note" in test_data:
                    files.append(("edit_note", (None, test_data["edit_note"])))
                
                response = requests.post(BASE_URL, headers=HEADERS, files=files)
                return response
    
    
    def test_01_basic_push_without_notes(self):
        """Базовый push без reupload_note и edit_note"""
        test_data = BASE_TEST_DATA.copy()
        test_data["uidSPUnit"] = "test_basic_001"
        test_data["cadastral_number"] = "cadastral_basic_001"
        
        response = self._make_request(test_data)
        
        print(f"\n✓ Test: Basic push without notes")
        print(f"  Status: {response.status_code}")
        print(f"  Response: {response.text}")
        
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
    
    
    def test_02_push_with_reupload_note_short(self):
        test_data = BASE_TEST_DATA.copy()
        test_data["uidSPUnit"] = "test_reupload_short_001"
        test_data["cadastral_number"] = "cadastral_reupload_short_001"
        test_data["reupload_note"] = "Повторная загрузка"
        
        response = self._make_request(test_data)
        
        print(f"\n✓ Test: Push with short reupload_note")
        print(f"  reupload_note: {test_data['reupload_note']}")
        print(f"  Status: {response.status_code}")
        print(f"  Response: {response.text}")
        
        assert response.status_code == 201
    
    def test_03_push_with_reupload_note_long(self):
        test_data = BASE_TEST_DATA.copy()
        test_data["uidSPUnit"] = "test_reupload_long_001"
        test_data["cadastral_number"] = "cadastral_reupload_long_001"
        test_data["reupload_note"] = (
            "Повторная загрузка документов в связи с исправлением ошибок "
            "в первоначальной версии. Были обновлены координаты границ участка "
            "и исправлены данные о правообладателях."
        )
        
        response = self._make_request(test_data)
        
        print(f"\n✓ Test: Push with long reupload_note")
        print(f"  reupload_note length: {len(test_data['reupload_note'])} chars")
        print(f"  Status: {response.status_code}")
        print(f"  Response: {response.text}")
        
        assert response.status_code == 201
    
    def test_04_push_with_reupload_note_special_chars(self):
        test_data = BASE_TEST_DATA.copy()
        test_data["uidSPUnit"] = "test_reupload_special_001"
        test_data["cadastral_number"] = "cadastral_reupload_special_001"
        test_data["reupload_note"] = "Исправление: координаты №1, площадь ~500м², дата 01.01.2024 @ 12:00"
        
        response = self._make_request(test_data)
        
        print(f"\n✓ Test: Push with special characters in reupload_note")
        print(f"  reupload_note: {test_data['reupload_note']}")
        print(f"  Status: {response.status_code}")
        print(f"  Response: {response.text}")
        
        assert response.status_code == 201
    
    def test_05_push_with_reupload_note_unicode(self):
        test_data = BASE_TEST_DATA.copy()
        test_data["uidSPUnit"] = "test_reupload_unicode_001"
        test_data["cadastral_number"] = "cadastral_reupload_unicode_001"
        test_data["reupload_note"] = "Re-upload: Ўзбекистон Республикаси - Uzbekistan Republic"
        
        response = self._make_request(test_data)
        
        print(f"\n✓ Test: Push with unicode in reupload_note")
        print(f"  reupload_note: {test_data['reupload_note']}")
        print(f"  Status: {response.status_code}")
        print(f"  Response: {response.text}")
        
        assert response.status_code == 201
    
    def test_06_push_with_empty_reupload_note(self):
        test_data = BASE_TEST_DATA.copy()
        test_data["uidSPUnit"] = "test_reupload_empty_001"
        test_data["cadastral_number"] = "cadastral_reupload_empty_001"
        test_data["reupload_note"] = ""
        
        response = self._make_request(test_data)
        
        print(f"\n✓ Test: Push with empty reupload_note")
        print(f"  Status: {response.status_code}")
        print(f"  Response: {response.text}")
        
        assert response.status_code in [201, 400, 422]

    
    def test_07_push_with_edit_note_short(self):
        """Push с коротким edit_note"""
        test_data = BASE_TEST_DATA.copy()
        test_data["uidSPUnit"] = "test_edit_short_001"
        test_data["cadastral_number"] = "cadastral_edit_short_001"
        test_data["edit_note"] = "Редактирование данных"
        
        response = self._make_request(test_data)
        
        print(f"\n✓ Test: Push with short edit_note")
        print(f"  edit_note: {test_data['edit_note']}")
        print(f"  Status: {response.status_code}")
        print(f"  Response: {response.text}")
        
        assert response.status_code == 201
    
    def test_08_push_with_edit_note_long(self):
        test_data = BASE_TEST_DATA.copy()
        test_data["uidSPUnit"] = "test_edit_long_001"
        test_data["cadastral_number"] = "cadastral_edit_long_001"
        test_data["edit_note"] = (
            "Редактирование записи кадастрового учета. Изменения внесены в следующие поля: "
            "адрес земельного участка, категория земель, вид разрешенного использования. "
            "Причина редактирования: обнаружены неточности в первоначальных данных. "
            "Редактирование произведено на основании распоряжения хокима."
        )
        
        response = self._make_request(test_data)
        
        print(f"\n✓ Test: Push with long edit_note")
        print(f"  edit_note length: {len(test_data['edit_note'])} chars")
        print(f"  Status: {response.status_code}")
        print(f"  Response: {response.text}")
        
        assert response.status_code == 201
    
    def test_09_push_with_edit_note_numbered_list(self):
        test_data = BASE_TEST_DATA.copy()
        test_data["uidSPUnit"] = "test_edit_list_001"
        test_data["cadastral_number"] = "cadastral_edit_list_001"
        test_data["edit_note"] = (
            "Внесены следующие изменения:\n"
            "1. Обновлен адрес участка\n"
            "2. Изменена категория земель\n"
            "3. Добавлен новый правообладатель\n"
            "4. Уточнены границы участка"
        )
        
        response = self._make_request(test_data)
        
        print(f"\n✓ Test: Push with numbered list in edit_note")
        print(f"  edit_note:\n{test_data['edit_note']}")
        print(f"  Status: {response.status_code}")
        print(f"  Response: {response.text}")
        
        assert response.status_code == 201
    
    def test_10_push_with_empty_edit_note(self):
        test_data = BASE_TEST_DATA.copy()
        test_data["uidSPUnit"] = "test_edit_empty_001"
        test_data["cadastral_number"] = "cadastral_edit_empty_001"
        test_data["edit_note"] = ""
        
        response = self._make_request(test_data)
        
        print(f"\n✓ Test: Push with empty edit_note")
        print(f"  Status: {response.status_code}")
        print(f"  Response: {response.text}")
        
        assert response.status_code in [201, 400, 422]
    
    def test_11_push_with_both_notes(self):
        """Push с обоими полями: reupload_note и edit_note"""
        test_data = BASE_TEST_DATA.copy()
        test_data["uidSPUnit"] = "test_both_notes_001"
        test_data["cadastral_number"] = "cadastral_both_notes_001"
        test_data["reupload_note"] = "Повторная загрузка документов"
        test_data["edit_note"] = "Редактирование границ участка"
        
        response = self._make_request(test_data)
        
        print(f"\n✓ Test: Push with both notes")
        print(f"  reupload_note: {test_data['reupload_note']}")
        print(f"  edit_note: {test_data['edit_note']}")
        print(f"  Status: {response.status_code}")
        print(f"  Response: {response.text}")
        
        assert response.status_code == 201
    
    def test_12_push_with_both_notes_long(self):
        test_data = BASE_TEST_DATA.copy()
        test_data["uidSPUnit"] = "test_both_long_001"
        test_data["cadastral_number"] = "cadastral_both_long_001"
        test_data["reupload_note"] = (
            "Повторная загрузка связана с необходимостью замены документов. "
            "Первоначальные документы содержали технические ошибки."
        )
        test_data["edit_note"] = (
            "Редактирование произведено в полях: адрес, категория земель, вид использования. "
            "Изменения внесены на основании распоряжения администрации."
        )
        
        response = self._make_request(test_data)
        
        print(f"\n✓ Test: Push with both long notes")
        print(f"  reupload_note length: {len(test_data['reupload_note'])} chars")
        print(f"  edit_note length: {len(test_data['edit_note'])} chars")
        print(f"  Status: {response.status_code}")
        print(f"  Response: {response.text}")
        
        assert response.status_code == 201
    
    def test_13_push_with_very_long_reupload_note(self):
        test_data = BASE_TEST_DATA.copy()
        test_data["uidSPUnit"] = "test_reupload_verylong_001"
        test_data["cadastral_number"] = "cadastral_reupload_verylong_001"
        test_data["reupload_note"] = "A" * 5000  # 5000 символов
        
        response = self._make_request(test_data)
        
        print(f"\n✓ Test: Push with very long reupload_note")
        print(f"  reupload_note length: {len(test_data['reupload_note'])} chars")
        print(f"  Status: {response.status_code}")
        print(f"  Response: {response.text[:200]}...")
        
        assert response.status_code in [201, 400, 413, 422]
    
    def test_14_push_with_sql_injection_in_notes(self):
        test_data = BASE_TEST_DATA.copy()
        test_data["uidSPUnit"] = "test_security_sql_001"
        test_data["cadastral_number"] = "cadastral_security_sql_001"
        test_data["reupload_note"] = "'; DROP TABLE cadastre; --"
        test_data["edit_note"] = "' OR '1'='1"
        
        response = self._make_request(test_data)
        
        print(f"\n✓ Test: Push with SQL injection attempt")
        print(f"  Status: {response.status_code}")
        print(f"  Response: {response.text}")
        
        assert response.status_code in [201, 400, 422]
    
    def test_15_push_with_html_in_notes(self):
        test_data = BASE_TEST_DATA.copy()
        test_data["uidSPUnit"] = "test_html_001"
        test_data["cadastral_number"] = "cadastral_html_001"
        test_data["reupload_note"] = "<script>alert('XSS')</script> Повторная загрузка"
        test_data["edit_note"] = "<b>Редактирование</b> <i>данных</i>"
        
        response = self._make_request(test_data)
        
        print(f"\n✓ Test: Push with HTML in notes")
        print(f"  Status: {response.status_code}")
        print(f"  Response: {response.text}")
        
        assert response.status_code in [201, 400, 422]

@pytest.mark.parametrize("reupload_note", [
    "Краткая заметка",
    "Повторная загрузка в связи с исправлением ошибок",
    "Re-upload: technical correction",
    "Загрузка №2 - исправление координат",
    "Повторная загрузка\nВторая строка\nТретья строка",
])
def test_16_parametrized_reupload_notes(reupload_note):
    test_data = BASE_TEST_DATA.copy()
    test_data["uidSPUnit"] = f"test_param_reupload_{hash(reupload_note) % 10000}"
    test_data["cadastral_number"] = f"cadastral_param_reupload_{hash(reupload_note) % 10000}"
    test_data["reupload_note"] = reupload_note
    
    if not os.path.exists(PDF_FILE_PATH):
        pytest.skip(f"PDF file not found: {PDF_FILE_PATH}")
    
    with open(PDF_FILE_PATH, "rb") as file1:
        with open(PDF_FILE_PATH, "rb") as file2:
            files = [
                ("uidSPUnit", (None, test_data["uidSPUnit"])),
                ("cadastral_number", (None, test_data["cadastral_number"])),
                ("address", (None, test_data["address"])),
                ("land_fund_type_code", (None, test_data["land_fund_type_code"])),
                ("land_use_type_code", (None, test_data["land_use_type_code"])),
                ("vid", (None, test_data["vid"])),
                ("region_soato", (None, test_data["region_soato"])),
                ("district_soato", (None, test_data["district_soato"])),
                ("neighborhood_soato", (None, test_data["neighborhood_soato"])),
                ("law_accordance_id", (None, test_data["law_accordance_id"])),
                ("selected_at", (None, test_data["selected_at"])),
                ("step_deadline", (None, test_data["step_deadline"])),
                ("location", (None, json.dumps(test_data["location"]))),
                ("building_land_cad_plan", ("land_plan.pdf", file1, "application/pdf")),
                ("governor_decree", ("decree.pdf", file2, "application/pdf")),
                ("mulk_egalari", (None, json.dumps(test_data["mulk_egalari"]))),
                ("reupload_note", (None, reupload_note)),
            ]
            
            response = requests.post(BASE_URL, headers=HEADERS, files=files)
            
            print(f"\n✓ Parametrized test reupload_note: {reupload_note[:50]}...")
            print(f"  Status: {response.status_code}")
            
            assert response.status_code == 201


@pytest.mark.parametrize("edit_note", [
    "Исправление адреса",
    "Редактирование категории земель и вида использования",
    "Edit: updated owner information",
    "Изменение №3 - обновление границ",
    "Редактирование:\n- Адрес\n- Площадь\n- Координаты",
])
def test_17_parametrized_edit_notes(edit_note):
    """Параметризованный тест различных edit_note"""
    test_data = BASE_TEST_DATA.copy()
    test_data["uidSPUnit"] = f"test_param_edit_{hash(edit_note) % 10000}"
    test_data["cadastral_number"] = f"cadastral_param_edit_{hash(edit_note) % 10000}"
    test_data["edit_note"] = edit_note
    
    if not os.path.exists(PDF_FILE_PATH):
        pytest.skip(f"PDF file not found: {PDF_FILE_PATH}")
    
    with open(PDF_FILE_PATH, "rb") as file1:
        with open(PDF_FILE_PATH, "rb") as file2:
            files = [
                ("uidSPUnit", (None, test_data["uidSPUnit"])),
                ("cadastral_number", (None, test_data["cadastral_number"])),
                ("address", (None, test_data["address"])),
                ("land_fund_type_code", (None, test_data["land_fund_type_code"])),
                ("land_use_type_code", (None, test_data["land_use_type_code"])),
                ("vid", (None, test_data["vid"])),
                ("region_soato", (None, test_data["region_soato"])),
                ("district_soato", (None, test_data["district_soato"])),
                ("neighborhood_soato", (None, test_data["neighborhood_soato"])),
                ("law_accordance_id", (None, test_data["law_accordance_id"])),
                ("selected_at", (None, test_data["selected_at"])),
                ("step_deadline", (None, test_data["step_deadline"])),
                ("location", (None, json.dumps(test_data["location"]))),
                ("building_land_cad_plan", ("land_plan.pdf", file1, "application/pdf")),
                ("governor_decree", ("decree.pdf", file2, "application/pdf")),
                ("mulk_egalari", (None, json.dumps(test_data["mulk_egalari"]))),
                ("edit_note", (None, edit_note)),
            ]
            
            response = requests.post(BASE_URL, headers=HEADERS, files=files)
            
            print(f"\n✓ Parametrized test edit_note: {edit_note[:50]}...")
            print(f"  Status: {response.status_code}")
            
            assert response.status_code == 201


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])