import math
from src.pdf_processor.inverter import load_product_config

CONFIG_PATH = "./config/health_and_accident_insurance.json"

# TODO: Implement multi-product support (e.g. personal accident, travel plans) and configurable discount thresholds.

def get_age_bracket_key(age: int, config: dict) -> str:
    """Finds the age bracket key (e.g. '31-35') for the given age."""
    brackets = config.get("age_brackets", [])
    for b in brackets:
        if b["min"] <= age <= b["max"]:
            return b["key"]
    return None

def get_deductible_discount(age: int, deductible_amount: int, config: dict) -> float:
    """Calculates the deductible discount percentage based on age and deductible amount."""
    if not deductible_amount or int(deductible_amount) == 0:
        return 0.0
        
    # Determine age bracket for deductible discount
    if age <= 40:
        bracket = "0-40"
    elif age <= 60:
        bracket = "41-60"
    else:
        bracket = "61+"
        
    discounts = config.get("deductible_discounts", {})
    age_discounts = discounts.get(bracket, {})
    return age_discounts.get(str(deductible_amount), 0.0)

def calculate_all_plans_premiums(coverage_key: str, deductible_amount: int, members: dict, config: dict = None) -> list[dict]:
    """
    Computes premium details for all 4 plan levels simultaneously, matching AXA calculator logic.
    """
    if config is None:
        config = load_product_config(CONFIG_PATH)
        
    # 1. Collect all ages
    ages = [members["main_age"]]
    if members.get("cover_spouse", False):
        ages.append(members["spouse_age"])
        
    child_count = members.get("child_count", 0)
    for i in range(1, child_count + 1):
        ages.append(members.get(f"child_{i}_age", 10))
        
    # 2. Accumulate base premiums for each plan level (0 to 3)
    r = [0, 0, 0, 0]
    premium_tables = config.get("premium_tables", {})
    ipd_table = premium_tables.get("ipd", {})
    cov_table = premium_tables.get(coverage_key, {})
    
    for age in ages:
        bracket = get_age_bracket_key(age, config)
        if not bracket:
            continue
            
        f = ipd_table.get(bracket, [0, 0, 0, 0])
        g = cov_table.get(bracket, [0, 0, 0, 0])
        
        # Deductible discount fraction
        h = get_deductible_discount(age, deductible_amount, config)
        
        for S in range(4):
            p = f[S]  # IPD only base premium
            v = g[S] - p  # OPD only portion
            
            # Discounted IPD portion
            m = math.ceil(p * (1.0 - h))
            
            # Member total for plan level S
            y = math.ceil(m + v)
            r[S] += y
            
    # 3. Apply family discount
    o = len(ages)
    i = 0.0
    if o >= 2 and o <= 3:
        i = 0.05
    elif o >= 4:
        i = 0.10
        
    final_premiums = [math.ceil(total * (1.0 - i)) for total in r]
    avg_premiums = [math.ceil(total / o) if o > 0 else 0 for total in final_premiums]
    
    plans_config = config.get("plans", [])
    results = []
    for idx, plan in enumerate(plans_config):
        results.append({
            "key": plan["key"],
            "label": plan["label"],
            "coverage": plan["coverage"],
            "room_limit": plan["room_limit"],
            "total": final_premiums[idx],
            "avg": avg_premiums[idx]
        })
        
    return results

def calculate_single_option_premium(plan_key: str, coverage_key: str, deductible_amount: int, members: dict, config: dict = None) -> dict:
    """
    Computes premium details for a single specific combination of plan, coverage, and deductible.
    """
    if config is None:
        config = load_product_config(CONFIG_PATH)
        
    plans_config = config.get("plans", [])
    plan_idx = 0
    for idx, plan in enumerate(plans_config):
        if plan["key"] == plan_key:
            plan_idx = idx
            break
            
    all_plans = calculate_all_plans_premiums(coverage_key, deductible_amount, members, config)
    return all_plans[plan_idx]
