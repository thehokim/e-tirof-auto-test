import pytest
import requests
import json

BASE_URL = "https://etirof.cmspace.uz/api/cadastre/integration/push"
HEADERS = {"Authorization": "Basic Y2FkYXN0cmU6Y2FkNTY3QUFA"}

@pytest.mark.parametrize("test_data", [
    {
        "uidSPUnit": "test15354123123dsawdrewresadawh12",
        "cadastral_number": "1234534512314321adwadwawasdwadwh12",
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
])
def test_push_integration(test_data):
    file_path = "/home/user/Downloads/12636_2_230FF8971C606F9DCE94288E49178A0490EBD387.pdf"

    with open(file_path, "rb") as file1:
        with open(file_path, "rb") as file2:
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

            response = requests.post(BASE_URL, headers=HEADERS, files=files)
            print("\nStatus:", response.status_code)
            print("Response:", response.text)

            assert response.status_code == 201
