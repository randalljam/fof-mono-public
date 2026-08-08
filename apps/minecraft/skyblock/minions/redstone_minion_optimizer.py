# ===== START OF FILE redstone_minion_optimizer.py =====
# Redstone Minion optimization tool for Hypixel Skyblock
# Analyzes current minions and recommends optimal upgrade/expansion strategy

import json
import re
from pathlib import Path


def load_minion_data(file_path="redstone_minion_data.json"):
    """
    Load minion tier data and prices from JSON reference file.

    :param file_path: string, path to the JSON data file.
    :return data: dict, minion tier info and current prices.
    """
    with open(file_path, 'r') as f:
        return json.load(f)
def parse_input_file(file_path="redstone_minion_input.md"):
    """
    Parse the markdown input file for current minions and settings.

    :param file_path: string, path to the markdown input file.
    :return config: dict, contains current_minions list, slot settings, and budget.
    """
    with open(file_path, 'r') as f:
        content = f.read()
    
    config = {
        'current_minions': [],
        'total_slots': 19,
        'willing_to_use': 10,
        'budget_coins': 1000000,
        'current_collection': 0,
        'current_collection_tier': 0
    }
    
    # Parse current minions section
    minions_match = re.search(r'## Current Minions\n.*?\n([\d\n]+)', content, re.DOTALL)
    if minions_match:
        minion_text = minions_match.group(1)
        for line in minion_text.strip().split('\n'):
            line = line.strip()
            if line.isdigit():
                config['current_minions'].append(int(line))
    
    # Parse settings
    total_match = re.search(r'total_slots:\s*(\d+)', content)
    if total_match:
        config['total_slots'] = int(total_match.group(1))
    
    willing_match = re.search(r'willing_to_use:\s*(\d+)', content)
    if willing_match:
        config['willing_to_use'] = int(willing_match.group(1))
    
    budget_match = re.search(r'budget_coins:\s*(\d+)', content)
    if budget_match:
        config['budget_coins'] = int(budget_match.group(1))
    
    # Parse collection progress
    collection_match = re.search(r'current_collection:\s*(\d+)', content)
    if collection_match:
        config['current_collection'] = int(collection_match.group(1))
    
    collection_tier_match = re.search(r'current_collection_tier:\s*(\d+)', content)
    if collection_tier_match:
        config['current_collection_tier'] = int(collection_tier_match.group(1))
    
    return config
def _get_upgrade_cost_coins(from_tier, to_tier, minion_data, prices):
    """
    Calculate coin cost to upgrade a minion from one tier to another.

    :param from_tier: integer, starting tier (use 0 for building new minion).
    :param to_tier: integer, target tier.
    :param minion_data: dict, minion tier information.
    :param prices: dict, current item prices.
    :return cost: float, total coin cost for the upgrade.
    """
    total_cost = 0.0
    
    for tier in range(from_tier + 1, to_tier + 1):
        tier_info = minion_data[str(tier)]
        upgrade = tier_info['upgrade_cost']
        item = upgrade['item']
        amount = upgrade['amount']
        total_cost += amount * prices[item]
    
    return total_cost
def _get_production_rate(tier, minion_data):
    """
    Get the actions per minute for a given minion tier.

    :param tier: integer, minion tier level.
    :param minion_data: dict, minion tier information.
    :return rate: float, actions per minute.
    """
    return minion_data[str(tier)]['actions_per_minute']
def _calculate_total_production(minion_tiers, minion_data):
    """
    Calculate total production rate for a set of minions.

    :param minion_tiers: list, tier levels of all minions.
    :param minion_data: dict, minion tier information.
    :return total: float, combined actions per minute.
    """
    return sum(_get_production_rate(tier, minion_data) for tier in minion_tiers)
def _generate_upgrade_options(current_minions, max_slots, minion_data, prices, budget):
    """
    Generate all possible upgrade/expansion combinations within budget.

    :param current_minions: list, current minion tier levels.
    :param max_slots: integer, maximum number of minion slots available.
    :param minion_data: dict, minion tier information.
    :param prices: dict, current item prices.
    :param budget: float, available coins to spend.
    :return options: list, each option is a dict with new_minions, cost, and production.
    """
    options = []
    max_tier = 11
    
    # Start with current state as baseline
    current_production = _calculate_total_production(current_minions, minion_data)
    options.append({
        'description': 'No changes (baseline)',
        'new_minions': list(current_minions),
        'cost': 0,
        'production': current_production,
        'production_gain': 0,
        'actions': []
    })
    
    # Try upgrading existing minions
    for i, current_tier in enumerate(current_minions):
        for target_tier in range(current_tier + 1, max_tier + 1):
            cost = _get_upgrade_cost_coins(current_tier, target_tier, minion_data, prices)
            if cost <= budget:
                new_minions = list(current_minions)
                new_minions[i] = target_tier
                production = _calculate_total_production(new_minions, minion_data)
                options.append({
                    'description': f'Upgrade minion #{i+1} from T{current_tier} to T{target_tier}',
                    'new_minions': new_minions,
                    'cost': cost,
                    'production': production,
                    'production_gain': production - current_production,
                    'actions': [f'Upgrade minion #{i+1}: T{current_tier} -> T{target_tier}']
                })
    
    # Try building new minions (if slots available)
    slots_available = max_slots - len(current_minions)
    if slots_available > 0:
        for new_tier in range(1, max_tier + 1):
            cost = _get_upgrade_cost_coins(0, new_tier, minion_data, prices)
            if cost <= budget:
                new_minions = list(current_minions) + [new_tier]
                production = _calculate_total_production(new_minions, minion_data)
                options.append({
                    'description': f'Build new T{new_tier} minion',
                    'new_minions': new_minions,
                    'cost': cost,
                    'production': production,
                    'production_gain': production - current_production,
                    'actions': [f'Build new minion at T{new_tier}']
                })
    
    return options
def _find_optimal_combination(current_minions, max_slots, minion_data, prices, budget, depth=0, memo=None):
    """
    Recursively find optimal combination of upgrades and new minions.

    :param current_minions: list, current minion tier levels.
    :param max_slots: integer, maximum number of minion slots available.
    :param minion_data: dict, minion tier information.
    :param prices: dict, current item prices.
    :param budget: float, remaining coins to spend.
    :param depth: integer, recursion depth for limiting search.
    :param memo: dict, memoization cache.
    :return best: dict, optimal configuration with cost and production.
    """
    if memo is None:
        memo = {}
    
    # Create state key for memoization
    state_key = (tuple(sorted(current_minions)), round(budget, 2))
    if state_key in memo:
        return memo[state_key]
    
    max_tier = 11
    current_production = _calculate_total_production(current_minions, minion_data)
    
    best = {
        'new_minions': list(current_minions),
        'cost_spent': 0,
        'production': current_production,
        'actions': []
    }
    
    # Limit depth to prevent excessive recursion
    if depth > 15:
        return best
    
    # Try upgrading each existing minion by one tier
    for i, current_tier in enumerate(current_minions):
        if current_tier < max_tier:
            target_tier = current_tier + 1
            cost = _get_upgrade_cost_coins(current_tier, target_tier, minion_data, prices)
            
            if cost <= budget:
                # Make upgrade and recurse
                upgraded_minions = list(current_minions)
                upgraded_minions[i] = target_tier
                
                result = _find_optimal_combination(
                    upgraded_minions, max_slots, minion_data, prices, 
                    budget - cost, depth + 1, memo
                )
                
                total_production = result['production']
                total_cost = cost + result['cost_spent']
                
                if total_production > best['production']:
                    best = {
                        'new_minions': result['new_minions'],
                        'cost_spent': total_cost,
                        'production': total_production,
                        'actions': [f'Upgrade minion #{i+1}: T{current_tier} -> T{target_tier}'] + result['actions']
                    }
    
    # Try adding a new minion (start at T1)
    slots_available = max_slots - len(current_minions)
    if slots_available > 0:
        new_tier = 1
        cost = _get_upgrade_cost_coins(0, new_tier, minion_data, prices)
        
        if cost <= budget:
            new_minions = list(current_minions) + [new_tier]
            
            result = _find_optimal_combination(
                new_minions, max_slots, minion_data, prices,
                budget - cost, depth + 1, memo
            )
            
            total_production = result['production']
            total_cost = cost + result['cost_spent']
            
            if total_production > best['production']:
                best = {
                    'new_minions': result['new_minions'],
                    'cost_spent': total_cost,
                    'production': total_production,
                    'actions': [f'Build new minion at T{new_tier}'] + result['actions']
                }
    
    memo[state_key] = best
    return best
def _consolidate_actions(actions, num_existing_minions):
    """
    Consolidate sequential upgrade actions into single upgrade paths.

    :param actions: list, raw action strings from optimization.
    :param num_existing_minions: integer, count of original minions before optimization.
    :return consolidated: list, cleaned up action descriptions.
    """
    # Track upgrades per minion
    upgrades = {}  # minion_id -> (start_tier, end_tier)
    new_minion_upgrades = {}  # tracks new minion index -> final tier
    new_minion_count = 0
    
    for action in actions:
        if 'Upgrade minion #' in action:
            match = re.search(r'Upgrade minion #(\d+): T(\d+) -> T(\d+)', action)
            if match:
                minion_id = int(match.group(1))
                from_tier = int(match.group(2))
                to_tier = int(match.group(3))
                
                # Check if this is an existing minion or a new one
                if minion_id <= num_existing_minions:
                    if minion_id in upgrades:
                        upgrades[minion_id] = (upgrades[minion_id][0], to_tier)
                    else:
                        upgrades[minion_id] = (from_tier, to_tier)
                else:
                    # This is upgrading a newly built minion
                    new_idx = minion_id - num_existing_minions
                    if new_idx in new_minion_upgrades:
                        new_minion_upgrades[new_idx] = max(new_minion_upgrades[new_idx], to_tier)
                    else:
                        new_minion_upgrades[new_idx] = to_tier
        
        elif 'Build new minion' in action:
            new_minion_count += 1
            if new_minion_count not in new_minion_upgrades:
                new_minion_upgrades[new_minion_count] = 1
    
    consolidated = []
    for minion_id, (from_tier, to_tier) in sorted(upgrades.items()):
        consolidated.append(f'Upgrade minion #{minion_id}: T{from_tier} -> T{to_tier}')
    
    for idx, tier in sorted(new_minion_upgrades.items()):
        consolidated.append(f'Build new minion #{idx} at T{tier}')
    
    return consolidated
def _format_coins(amount):
    """
    Format coin amount with commas, rounded to whole number.

    :param amount: float, coin amount.
    :return formatted: string, formatted coin string.
    """
    return f"{round(amount):,}"

def _calc_enchanted_dust_per_day(actions_per_min, dust_per_enchanted):
    """
    Calculate enchanted redstone dust production per day.

    :param actions_per_min: float, total actions per minute (each action = 1 dust).
    :param dust_per_enchanted: integer, redstone dust needed for 1 enchanted dust.
    :return enchanted_per_day: float, enchanted redstone dust produced per day.
    """
    dust_per_day = actions_per_min * 60 * 24
    return dust_per_day / dust_per_enchanted

def _calc_dust_per_day(actions_per_min):
    """
    Calculate redstone dust production per day.

    :param actions_per_min: float, total actions per minute (each action = 1 dust).
    :return dust_per_day: float, redstone dust produced per day.
    """
    return actions_per_min * 60 * 24

def _calc_time_to_collection_tier(current_collected, target_required, dust_per_day):
    """
    Calculate days needed to reach a collection tier.

    :param current_collected: integer, current total redstone dust collected.
    :param target_required: integer, dust required for the target tier.
    :param dust_per_day: float, daily dust production rate.
    :return days: float, days needed (0 if already reached, None if impossible).
    """
    if current_collected >= target_required:
        return 0
    if dust_per_day <= 0:
        return None
    remaining = target_required - current_collected
    return remaining / dust_per_day

def _format_time(days):
    """
    Format days into a human-readable string.

    :param days: float, number of days.
    :return formatted: string, formatted time string.
    """
    if days is None:
        return "N/A"
    if days == 0:
        return "Already reached!"
    if days < 1:
        hours = days * 24
        return f"{hours:.1f} hours"
    if days < 7:
        return f"{days:.1f} days"
    weeks = days / 7
    if weeks < 4:
        return f"{weeks:.1f} weeks"
    months = days / 30
    return f"{months:.1f} months"

def _calc_collection_tier_times(current_collected, collection_tiers, dust_per_day, current_tier, num_future_tiers=5):
    """
    Calculate time to reach multiple future collection tiers.

    :param current_collected: integer, current total dust collected.
    :param collection_tiers: dict, collection tier data.
    :param dust_per_day: float, daily dust production rate.
    :param current_tier: integer, current collection tier.
    :param num_future_tiers: integer, how many future tiers to show.
    :return tier_times: list, dicts with tier info and time to reach.
    """
    tier_times = []
    max_tier = max(int(t) for t in collection_tiers.keys())
    
    for tier_num in range(current_tier + 1, min(current_tier + num_future_tiers + 1, max_tier + 1)):
        tier_key = str(tier_num)
        if tier_key in collection_tiers:
            required = collection_tiers[tier_key]['required']
            days = _calc_time_to_collection_tier(current_collected, required, dust_per_day)
            tier_times.append({
                'tier': tier_num,
                'required': required,
                'remaining': max(0, required - current_collected),
                'days': days,
                'time_str': _format_time(days)
            })
    
    return tier_times

def optimize_minions(data_file_path="redstone_minion_data.json", input_file_path="redstone_minion_input.md"):
    """
    Main optimization function that analyzes current minions and recommends strategy.

    :param data_file_path: string, path to minion data JSON file.
    :param input_file_path: string, path to input markdown file.
    :return result: dict, contains current state, optimal strategy, and comparison.
    """
    # Load data
    data = load_minion_data(data_file_path)
    config = parse_input_file(input_file_path)
    
    minion_data = data['minion_tiers']
    prices = data['prices']
    conversion = data['conversion']
    collection_tiers = data['collection_tiers']
    dust_per_enchanted = conversion['dust_per_enchanted_dust']
    
    current_minions = config['current_minions']
    max_slots = config['willing_to_use']
    budget = config['budget_coins']
    current_collection = config['current_collection']
    current_collection_tier = config['current_collection_tier']
    
    # Calculate current state
    current_production = _calculate_total_production(current_minions, minion_data)
    current_enchanted_per_day = _calc_enchanted_dust_per_day(current_production, dust_per_enchanted)
    current_dust_per_day = _calc_dust_per_day(current_production)
    
    # Find optimal combination
    optimal = _find_optimal_combination(current_minions, max_slots, minion_data, prices, budget)
    optimal_enchanted_per_day = _calc_enchanted_dust_per_day(optimal['production'], dust_per_enchanted)
    optimal_dust_per_day = _calc_dust_per_day(optimal['production'])
    
    # Calculate time to collection tiers (before and after optimization)
    current_tier_times = _calc_collection_tier_times(
        current_collection, collection_tiers, current_dust_per_day, current_collection_tier
    )
    optimal_tier_times = _calc_collection_tier_times(
        current_collection, collection_tiers, optimal_dust_per_day, current_collection_tier
    )
    
    # Consolidate actions for cleaner output
    consolidated_actions = _consolidate_actions(optimal['actions'], len(current_minions))
    
    # Build result
    result = {
        'current_state': {
            'minions': current_minions,
            'minion_count': len(current_minions),
            'action_rate': current_production,
            'dust_per_day': current_dust_per_day,
            'enchanted_dust_per_day': current_enchanted_per_day
        },
        'settings': {
            'total_slots': config['total_slots'],
            'willing_to_use': max_slots,
            'budget': budget
        },
        'collection': {
            'current_collected': current_collection,
            'current_tier': current_collection_tier,
            'tier_times_before': current_tier_times,
            'tier_times_after': optimal_tier_times
        },
        'optimal_strategy': {
            'new_minions': optimal['new_minions'],
            'minion_count': len(optimal['new_minions']),
            'cost_spent': optimal['cost_spent'],
            'remaining_budget': budget - optimal['cost_spent'],
            'action_rate': optimal['production'],
            'dust_per_day': optimal_dust_per_day,
            'enchanted_dust_per_day': optimal_enchanted_per_day,
            'actions': consolidated_actions
        },
        'comparison': {
            'action_rate_gain': optimal['production'] - current_production,
            'enchanted_dust_gain': optimal_enchanted_per_day - current_enchanted_per_day,
            'improvement_percent': ((optimal['production'] - current_production) / current_production * 100) if current_production > 0 else 0
        },
        'prices_used': prices,
        'conversion': conversion
    }
    
    return result
def print_optimization_report(result):
    """
    Print a formatted optimization report to console.

    :param result: dict, optimization result from optimize_minions().
    :return None: prints to console.
    """
    print("\n" + "=" * 70)
    print("=== REDSTONE MINION OPTIMIZATION REPORT ===")
    print("=" * 70)
    
    # Current State
    print("\n--- CURRENT STATE ---")
    current = result['current_state']
    print(f"Minions: {len(current['minions'])} minions")
    tier_str = ', '.join([f'T{t}' for t in current['minions']])
    print(f"Tiers: {tier_str}")
    print(f"Total Action Rate: {current['action_rate']:.2f} actions/min")
    print(f"Dust/Day: {_format_coins(current['dust_per_day'])}")
    print(f"Enchanted Dust/Day: {current['enchanted_dust_per_day']:.2f}")
    
    # Collection Progress
    print("\n--- COLLECTION PROGRESS ---")
    collection = result['collection']
    print(f"Current Collection Tier: {collection['current_tier']}")
    print(f"Total Collected: {_format_coins(collection['current_collected'])} dust")
    
    # Settings
    print("\n--- SETTINGS ---")
    settings = result['settings']
    print(f"Total Slots Available: {settings['total_slots']}")
    print(f"Willing to Use: {settings['willing_to_use']}")
    print(f"Budget: {_format_coins(settings['budget'])} coins")
    
    # Optimal Strategy
    print("\n--- OPTIMAL STRATEGY ---")
    optimal = result['optimal_strategy']
    print(f"Cost: {_format_coins(optimal['cost_spent'])} coins")
    print(f"Remaining Budget: {_format_coins(optimal['remaining_budget'])} coins")
    print(f"\nActions to Take:")
    if optimal['actions']:
        for action in optimal['actions']:
            print(f"  • {action}")
    else:
        print("  • No changes recommended within budget")
    
    # Resulting State
    print("\n--- RESULTING STATE ---")
    print(f"Minions: {optimal['minion_count']} minions")
    tier_str = ', '.join([f'T{t}' for t in optimal['new_minions']])
    print(f"Tiers: {tier_str}")
    print(f"Total Action Rate: {optimal['action_rate']:.2f} actions/min")
    print(f"Dust/Day: {_format_coins(optimal['dust_per_day'])}")
    print(f"Enchanted Dust/Day: {optimal['enchanted_dust_per_day']:.2f}")
    
    # Comparison
    print("\n--- IMPROVEMENT SUMMARY ---")
    comparison = result['comparison']
    print(f"Action Rate Gain: +{comparison['action_rate_gain']:.2f} actions/min")
    print(f"Enchanted Dust Gain: +{comparison['enchanted_dust_gain']:.2f}/day")
    print(f"Improvement: +{comparison['improvement_percent']:.1f}%")
    
    # Time to Collection Tiers
    print("\n--- TIME TO COLLECTION TIERS ---")
    tier_times_before = collection['tier_times_before']
    tier_times_after = collection['tier_times_after']
    
    if tier_times_before:
        print(f"{'Tier':<6} {'Required':<12} {'Remaining':<12} {'Before':<15} {'After':<15}")
        print("-" * 60)
        for before, after in zip(tier_times_before, tier_times_after):
            print(f"{before['tier']:<6} {_format_coins(before['required']):<12} {_format_coins(before['remaining']):<12} {before['time_str']:<15} {after['time_str']:<15}")
    else:
        print("  All tracked collection tiers reached!")
    
    # Price Info
    print("\n--- PRICES USED ---")
    prices = result['prices_used']
    print(f"Price Date: {prices['price_date']}")
    print(f"Redstone Dust: {_format_coins(prices['redstone_dust'])} coins")
    print(f"Enchanted Redstone Dust: {_format_coins(prices['enchanted_redstone_dust'])} coins")
    print(f"Enchanted Redstone Block: {_format_coins(prices['enchanted_redstone_block'])} coins")
    
    print("\n" + "=" * 70)
    print()
def run_optimization(data_file_path="redstone_minion_data.json", input_file_path="redstone_minion_input.md"):
    """
    Run the full optimization and print the report.

    :param data_file_path: string, path to minion data JSON file.
    :param input_file_path: string, path to input markdown file.
    :return result: dict, optimization results.
    """
    result = optimize_minions(data_file_path, input_file_path)
    print_optimization_report(result)
    return result
def mrun_optimize():
    pass
if __name__ == "__main__":
    folder = Path(__file__).parent
    data_file = folder / "redstone_minion_data.json"
    input_file = folder / "redstone_minion_input.md"
    run_optimization(str(data_file), str(input_file))


# ===== END OF FILE redstone_minion_optimizer.py =====
