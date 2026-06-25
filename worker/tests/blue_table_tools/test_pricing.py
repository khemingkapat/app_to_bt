import pytest
from src.pdf_processor.inverter import load_product_config
from src.blue_table_tools.pricing import get_age_bracket_key, get_deductible_discount, calculate_all_plans_premiums, calculate_single_option_premium

def test_get_age_bracket_key():
    config = load_product_config()
    brackets = config.get("age_brackets", [])
    if brackets:
        for b in brackets:
            assert get_age_bracket_key(b["min"], config) == b["key"]
            assert get_age_bracket_key(b["max"], config) == b["key"]
        
        # Check out of bounds age
        max_age = max(b["max"] for b in brackets)
        assert get_age_bracket_key(max_age + 1, config) is None
    else:
        assert get_age_bracket_key(5, config) == "0-5"
        assert get_age_bracket_key(25, config) == "21-25"
        assert get_age_bracket_key(40, config) == "36-40"
        assert get_age_bracket_key(64, config) == "61-64"
        assert get_age_bracket_key(70, config) is None

def test_get_deductible_discount():
    config = load_product_config()
    assert get_deductible_discount(30, 20000, config) == config["deductible_discounts"]["0-40"]["20000"]
    assert get_deductible_discount(30, 40000, config) == config["deductible_discounts"]["0-40"]["40000"]
    assert get_deductible_discount(30, 0, config) == 0.0

    assert get_deductible_discount(50, 20000, config) == config["deductible_discounts"]["41-60"]["20000"]
    assert get_deductible_discount(50, 100000, config) == config["deductible_discounts"]["41-60"]["100000"]

    assert get_deductible_discount(62, 20000, config) == config["deductible_discounts"]["61+"]["20000"]
    assert get_deductible_discount(62, 200000, config) == config["deductible_discounts"]["61+"]["200000"]

def test_calculate_all_plans_premiums_single():
    config = load_product_config()
    members = {
        "main_age": 25,
        "cover_spouse": False,
        "child_count": 0
    }

    # IPD only, deductible 0
    results = calculate_all_plans_premiums("ipd", 0, members, config)

    # Expected: bracket array: fetch from config
    bracket = get_age_bracket_key(25, config)
    expected = config["premium_tables"]["ipd"][bracket]
    assert results[0]["total"] == expected[0]
    assert results[1]["total"] == expected[1]
    assert results[2]["total"] == expected[2]
    assert results[3]["total"] == expected[3]

def test_calculate_all_plans_premiums_family_deductible():
    config = load_product_config()
    members = {
        "main_age": 40,
        "cover_spouse": True,
        "spouse_age": 30,
        "child_count": 0
    }

    results = calculate_all_plans_premiums("ipd_opd_3000", 20000, members, config)

    # Calculate expected totals dynamically
    import math
    bracket_40 = get_age_bracket_key(40, config)
    ipd_t = config["premium_tables"]["ipd"][bracket_40][0]
    opd_t = config["premium_tables"]["ipd_opd_3000"][bracket_40][0] - ipd_t
    h = get_deductible_discount(40, 20000, config)
    m1 = math.ceil(ipd_t * (1.0 - h)) + opd_t

    bracket_30 = get_age_bracket_key(30, config)
    ipd_t2 = config["premium_tables"]["ipd"][bracket_30][0]
    opd_t2 = config["premium_tables"]["ipd_opd_3000"][bracket_30][0] - ipd_t2
    m2 = math.ceil(ipd_t2 * (1.0 - h)) + opd_t2

    expected_total = math.ceil((m1 + m2) * 0.95)
    expected_avg = math.ceil(expected_total / 2)

    assert results[0]["total"] == expected_total
    assert results[0]["avg"] == expected_avg

def test_calculate_single_option_premium():
    config = load_product_config()
    members = {
        "main_age": 40,
        "cover_spouse": True,
        "spouse_age": 30,
        "child_count": 0
    }

    # Calculate single plan specifically (Plan 1)
    result = calculate_single_option_premium("Plan 1", "ipd_opd_3000", 20000, members, config)
    all_res = calculate_all_plans_premiums("ipd_opd_3000", 20000, members, config)

    assert result["total"] == all_res[0]["total"]
    assert result["coverage"] == config["plans"][0]["coverage"]
    assert result["room_limit"] == config["plans"][0]["room_limit"]

# TODO: Add edge-case test coverage for newborn infants (< 30 days) and senior applicants (ages 61-65) to verify premium calculations.
