def simulate_ocr(section_name: str, id_name: str, id_dob: str, id_addr: str) -> tuple[dict, dict]:
    """
    Simulates OCR processing without relying on UI components.
    Returns a dictionary of new form_data and a dictionary of new ocr_simulated flags.
    """
    new_data = {}
    new_simulated = {}

    if section_name == "Main":
        new_data.update({
            "dob": id_dob,
            "present_address": id_addr,
            "tel": "0812345678",
            "email": "alex.mercer@example.com",
            "nationality": "Thai",
            "occupation": "Engineer",
            "beneficiary": "Jane Mercer",
            "bene_relation": "Mother",
            "name": "",
            "id_card_no": ""
        })

        for key in ["dob", "present_address", "tel", "email", "nationality",
                    "occupation", "beneficiary", "bene_relation"]:
            new_simulated[f"Main_{key}"] = True

    elif section_name == "Spouse":
        new_data.update({
            "sp_dob": id_dob,
            "sp_nationality": "Thai",
            "sp_occupation": "Accountant",
            "sp_beneficiary": "Alex Mercer",
            "sp_bene_relation": "Husband",
            "sp_name": "",
            "sp_id_card_no": ""
        })

        for key in ["sp_dob", "sp_nationality", "sp_occupation",
                    "sp_beneficiary", "sp_bene_relation"]:
            new_simulated[f"Spouse_{key}"] = True

    return new_data, new_simulated
