import pytest
from src.pdf_processor.inverter import load_product_config
from src.blue_table_tools.pricing import get_age_multiplier, calculate_premium

def test_get_age_multiplier():
    config = load_product_config()
    
    # Brackets: 0-18 (0.8), 19-35 (1.0), 36-50 (1.25), 51-65 (1.6), 66+ (2.2)
    assert get_age_multiplier(10, config) == 0.8
    assert get_age_multiplier(25, config) == 1.0
    assert get_age_multiplier(40, config) == 1.25
    assert get_age_multiplier(60, config) == 1.6
    assert get_age_multiplier(70, config) == 2.2

def test_calculate_premium_basic():
    config = load_product_config()
    
    # Case: Basic Plan (12000 Base), No Spouse, No Kids, No Deductible, age 25 (1.0 mult)
    members = {
        "main_age": 25,
        "cover_spouse": False,
        "child_count": 0
    }
    
    premium, breakdown = calculate_premium("Basic", "None", members, config)
    assert premium == 12000.0
    assert breakdown["Main Insured"] == 12000.0

def test_calculate_premium_with_spouse_and_child():
    config = load_product_config()
    
    # Case: Standard Plan (24000 Base), Deductible 10k (0.85 mult)
    # Main: Age 40 (1.25 mult) -> cost = 24000 * 1.25 = 30000
    # Spouse: Age 30 (1.0 mult, 90% premium) -> cost = 24000 * 1.0 * 0.9 = 21600
    # Child 1: Age 8 (0.8 mult, 70% premium) -> cost = 24000 * 0.8 * 0.7 = 13440
    # Total before deductible = 30000 + 21600 + 13440 = 65040
    # After Deductible: 65040 * 0.85 = 55284
    members = {
        "main_age": 40,
        "cover_spouse": True,
        "spouse_age": 30,
        "child_count": 1,
        "child_1_age": 8
    }
    
    premium, breakdown = calculate_premium("Standard", "10k", members, config)
    
    assert breakdown["Main Insured"] == 30000.0
    assert breakdown["Spouse"] == 21600.0
    assert breakdown["Children"] == [13440.0]
    assert premium == 55284.0
