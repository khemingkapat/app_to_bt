from src.pdf_processor.inverter import load_product_config

CONFIG_PATH = "./config/health_and_accident.json"

def get_age_multiplier(age: int, config: dict) -> float:
    pricing = config.get("pricing", {})
    brackets = pricing.get("age_brackets", [])
    for b in brackets:
        if b["min"] <= age <= b["max"]:
            return b["multiplier"]
    return 1.0

def calculate_premium(plan_key: str, deductible_key: str, members: dict, config: dict = None) -> tuple[float, dict]:
    """
    Computes total premium and its breakdown based on plan, deductible, and family ages/options.
    """
    if config is None:
        config = load_product_config(CONFIG_PATH)
        
    pricing = config.get("pricing", {})
    
    # 1. Find Plan Base Premium
    base_premium = 0
    for p in pricing.get("plans", []):
        if p["key"] == plan_key:
            base_premium = p["base_premium"]
            break
            
    # 2. Find Deductible Multiplier
    deductible_multiplier = 1.0
    for d in pricing.get("deductibles", []):
        if d["key"] == deductible_key:
            deductible_multiplier = d["multiplier"]
            break
            
    # 3. Calculate Member Premiums
    total_premium = 0
    breakdown = {}
    
    # Main Insured
    main_age = members.get("main_age", 30)
    main_multiplier = get_age_multiplier(main_age, config)
    main_cost = base_premium * main_multiplier
    total_premium += main_cost
    breakdown["Main Insured"] = main_cost
    
    # Spouse
    if members.get("cover_spouse", False):
        spouse_age = members.get("spouse_age", 30)
        spouse_multiplier = get_age_multiplier(spouse_age, config)
        spouse_cost = base_premium * spouse_multiplier * pricing.get("spouse_premium_percentage", 0.90)
        total_premium += spouse_cost
        breakdown["Spouse"] = spouse_cost
        
    # Children
    child_count = members.get("child_count", 0)
    if child_count > 0:
        child_costs = []
        for i in range(1, child_count + 1):
            child_age = members.get(f"child_{i}_age", 10)
            child_multiplier = get_age_multiplier(child_age, config)
            child_cost = base_premium * child_multiplier * pricing.get("child_premium_percentage", 0.70)
            total_premium += child_cost
            child_costs.append(child_cost)
        breakdown["Children"] = child_costs
        
    # Apply Deductible
    final_premium = round(total_premium * deductible_multiplier, 2)
    
    return final_premium, breakdown
