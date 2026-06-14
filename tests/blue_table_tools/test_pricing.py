import pytest
from src.pdf_processor.inverter import load_product_config
from src.blue_table_tools.pricing import get_age_bracket_key, get_deductible_discount, calculate_all_plans_premiums

def test_get_age_bracket_key():
    config = load_product_config()
    assert get_age_bracket_key(5, config) == "0-5"
    assert get_age_bracket_key(25, config) == "21-25"
    assert get_age_bracket_key(40, config) == "36-40"
    assert get_age_bracket_key(64, config) == "61-64"
    assert get_age_bracket_key(70, config) is None

def test_get_deductible_discount():
    config = load_product_config()
    # Age <= 40: 20000 -> 0.45, 40000 -> 0.55
    assert get_deductible_discount(30, 20000, config) == 0.45
    assert get_deductible_discount(30, 40000, config) == 0.55
    assert get_deductible_discount(30, 0, config) == 0.0
    
    # Age 41-60: 20000 -> 0.30, 100000 -> 0.65
    assert get_deductible_discount(50, 20000, config) == 0.30
    assert get_deductible_discount(50, 100000, config) == 0.65
    
    # Age 61+: 20000 -> 0.10, 200000 -> 0.35
    assert get_deductible_discount(62, 20000, config) == 0.10
    assert get_deductible_discount(62, 200000, config) == 0.35

def test_calculate_all_plans_premiums_single():
    config = load_product_config()
    members = {
        "main_age": 25,
        "cover_spouse": False,
        "child_count": 0
    }
    
    # IPD only, deductible 0
    results = calculate_all_plans_premiums("ipd", 0, members, config)
    
    # Expected: "21-25" bracket array: [16380, 21215, 23045, 25345]
    # No discounts, 1 person
    assert results[0]["total"] == 16380
    assert results[1]["total"] == 21215
    assert results[2]["total"] == 23045
    assert results[3]["total"] == 25345

def test_calculate_all_plans_premiums_family_deductible():
    config = load_product_config()
    members = {
        "main_age": 40,
        "cover_spouse": True,
        "spouse_age": 30,
        "child_count": 0
    }
    
    # Coverage: ipd_opd_3000, deductible 20000
    # Main age 40: Bracket 36-40.
    # IPD Plan 1 = 21370, Total Plan 1 = 34415. OPD portion = 34415 - 21370 = 13045.
    # Deductible 20000 discount (age 40) = 45% (0.45).
    # Discounted IPD = ceil(21370 * (1 - 0.45)) = 11754.
    # Main Total Plan 1 = 11754 + 13045 = 24799.
    #
    # Spouse age 30: Bracket 26-30.
    # IPD Plan 1 = 17400, Total Plan 1 = 27770. OPD portion = 27770 - 17400 = 10370.
    # Deductible 20000 discount (age 30) = 45% (0.45).
    # Discounted IPD = ceil(17400 * (1 - 0.45)) = 9570.
    # Spouse Total Plan 1 = 9570 + 10370 = 19940.
    #
    # Total before family discount = 24799 + 19940 = 44739.
    # Family discount: 2 people -> 5% off.
    # Final Plan 1 = ceil(44739 * 0.95) = ceil(42502.05) = 42503.
    # Average = ceil(42503 / 2) = 21252.
    
    results = calculate_all_plans_premiums("ipd_opd_3000", 20000, members, config)
    
    assert results[0]["total"] == 42503
    assert results[0]["avg"] == 21252
