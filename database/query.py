import argparse
import json
import math
import re
from functools import lru_cache
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parent / "scraper" / "data"
PETS_PATH = DATA_DIR / "pets_detailed.json"
COUNTER_PATH = DATA_DIR / "counter_received_damage.json"


@lru_cache(maxsize=1)
def load_data():
    with open(PETS_PATH, "r", encoding="utf-8") as f:
        pets = json.load(f)
    try:
        with open(COUNTER_PATH, "r", encoding="utf-8") as f:
            counter = json.load(f)
    except Exception:
        counter = {}
    return pets, counter


def normalize_text(value):
    return re.sub(r"\s+", "", str(value or "")).lower()


def find_pets(name, pets):
    out = []
    q = normalize_text(name)
    for p in pets:
        title = normalize_text(p.get("wikitext_title") or "")
        display = normalize_text(p.get("name") or "")
        if q in title or q in display:
            out.append(p)
    return out


def get_pet_types(pet):
    types = []
    for attr in pet.get("attributes", []):
        key = attr.get("key") or ""
        value = attr.get("name") or ""
        if key in {"主属性", "副属性", "属性"} and value:
            types.append(value)
    return types


def _parse_first_number(text):
    if not text:
        return None
    match = re.search(r"(-?\d+(?:\.\d+)?)", str(text))
    if not match:
        return None
    return float(match.group(1))


def extract_power_bonus(content):
    """Parse phrases like '威力永久+30'. Return additive bonus as float."""
    if not content:
        return 0.0
    match = re.search(r"威力(?:永久)?\+\s*(\d+(?:\.\d+)?)", content)
    if match:
        return float(match.group(1))
    return 0.0


def extract_power_multiplier(content):
    """Parse phrases like '威力变为3倍'. Return multiplier as float."""
    if not content:
        return 1.0
    match = re.search(r"威力(?:变为|变成)\s*(\d+(?:\.\d+)?)\s*倍", content)
    if match:
        return float(match.group(1))
    return 1.0


def extract_reduction_rate(content):
    """Parse phrases like '减伤70%'. Return reduction as 0.7."""
    if not content:
        return 0.0
    match = re.search(r"减伤\s*(\d+(?:\.\d+)?)\s*%", content)
    if match:
        return float(match.group(1)) / 100.0
    return 0.0


def extract_response_multiplier(content):
    """Extract the multiplier used when a skill has an 应对 clause.

    If no explicit multiplier is present, fall back to 1.0.
    """
    if not content or "应对" not in content:
        return 1.0
    match = re.search(r"应对[^，。；;]*?威力(?:变为|变成)\s*(\d+(?:\.\d+)?)\s*倍", content)
    if match:
        return float(match.group(1))
    match = re.search(r"应对[^，。；;]*?\+\s*(\d+(?:\.\d+)?)", content)
    if match:
        # treat explicit additive response text as an additional multiplier proxy only when present
        return float(match.group(1))
    return 1.0


def pet_skills(name):
    pets, _ = load_data()
    found = find_pets(name, pets)
    if not found:
        return []
    # return skills for first matched pet
    return found[0].get("skills", [])


def pets_by_skill(skill_name):
    pets, _ = load_data()
    q = skill_name.strip().lower()
    out = []
    for p in pets:
        for s in p.get("skills", []):
            if q in (s.get("name") or "").lower():
                out.append(p.get("wikitext_title") or p.get("name"))
                break
    return out


def skill_info(skill_name):
    pets, _ = load_data()
    q = skill_name.strip().lower()
    for p in pets:
        for s in p.get("skills", []):
            if q in (s.get("name") or "").lower():
                # attach example owner
                s_copy = dict(s)
                s_copy["example_pet"] = p.get("wikitext_title") or p.get("name")
                return s_copy
    return {}


def pet_info(name):
    pets, _ = load_data()
    found = find_pets(name, pets)
    if not found:
        return {}
    p = found[0]
    return {
        "wikitext_title": p.get("wikitext_title"),
        "attributes": p.get("attributes", []),
        "qualification": p.get("qualification", {}),
        "characteristic": p.get("characteristic", {}),
        "skills_count": len(p.get("skills", [])),
    }


def compute_attr_bounds(name):
    pets, _ = load_data()
    found = find_pets(name, pets)
    if not found:
        return {}
    p = found[0]
    stats_map = p.get("qualification", {}).get("stats_map", {})
    # convert to ints (fallback 0)
    base = {k: int(v) if v and str(v).isdigit() else 0 for k, v in stats_map.items()}

    iv_low = 42
    iv_high = 60
    natures = [(-0.1, "nature_-0.1"), (0.2, "nature_+0.2")]
    ivs = [(iv_low, "iv_low"), (iv_high, "iv_high")]
    results = {}
    for iv_val, iv_name in ivs:
        for nat_val, nat_name in natures:
            key = f"{iv_name}|{nat_name}"
            attrs = {}
            # 生命
            hp = (1.7 * base.get("生命", 0) + iv_val * 0.85 + 70) * (1 + nat_val) + 100
            attrs["生命"] = math.floor(hp)
            for k in ("物攻", "魔攻", "物防", "魔防", "速度"):
                val = (1.1 * base.get(k, 0) + iv_val * 0.55 + 10) * (1 + nat_val) + 50
                attrs[k] = math.floor(val)
            results[key] = attrs
    return results


def pick_attr_variant(bounds, variant_key=None):
    if not bounds:
        return {}
    if variant_key and variant_key in bounds:
        return bounds[variant_key]
    return next(iter(bounds.values()))


def lookup_type_multiplier(counter, defender_types, skill_attr):
    if not counter:
        return 1.0
    defender_types = [t for t in defender_types if t]
    if not defender_types:
        return 1.0

    exact_keys = [
        {"defender_type": defender_types[0]},
        {"defender_types": defender_types[:2]},
    ]
    for entry in counter.get("single_type_rules", []):
        if entry.get("defender_type") == defender_types[0]:
            for inc in entry.get("received_damage_increased", []):
                if inc.get("type") == skill_attr:
                    return float(inc.get("multiplier", "1.0"))
            for dec in entry.get("received_damage_decreased", []):
                if dec.get("type") == skill_attr:
                    return float(dec.get("multiplier", "1.0"))

    for entry in counter.get("dual_type_rules", []):
        if sorted(entry.get("defender_types", [])) == sorted(defender_types[:2]):
            for inc in entry.get("received_damage_increased", []):
                if inc.get("type") == skill_attr:
                    return float(inc.get("multiplier", "1.0"))
            for dec in entry.get("received_damage_decreased", []):
                if dec.get("type") == skill_attr:
                    return float(dec.get("multiplier", "1.0"))
    return 1.0


def _find_counter_multiplier(counter, defender_type, skill_attr):
    if not counter:
        return 1.0
    # search single_type_rules
    for entry in counter.get("single_type_rules", []):
        if entry.get("defender_type") == defender_type:
            for inc in entry.get("received_damage_increased", []):
                if inc.get("type") == skill_attr:
                    return float(inc.get("multiplier", "1.0"))
            for dec in entry.get("received_damage_decreased", []):
                if dec.get("type") == skill_attr:
                    return float(dec.get("multiplier", "1.0"))
    return 1.0


def damage_breakdown(
    attacker_name,
    defender_name,
    skill_name,
    defender_skill_name=None,
    attacker_state_key=None,
    defender_state_key=None,
    attacker_attack_up=0.0,
    attacker_attack_down=0.0,
    defender_defense_up=0.0,
    defender_defense_down=0.0,
    weather=1.0,
    combo=1.0,
):
    pets, counter = load_data()
    atk_list = find_pets(attacker_name, pets)
    def_list = find_pets(defender_name, pets)
    if not atk_list or not def_list:
        return {"error": "attacker or defender not found"}
    atk = atk_list[0]
    df = def_list[0]

    # find skill on attacker
    skill = None
    for s in atk.get("skills", []):
        if (skill_name or "").strip().lower() in (s.get("name") or "").lower():
            skill = s
            break
    if not skill:
        return {"error": "skill not found on attacker"}

    try:
        skill_power = float(skill.get("damage") or skill.get("power") or 0)
    except Exception:
        skill_power = 0.0

    skill_type = normalize_text(skill.get("skill_type") or "")
    skill_attr = skill.get("attribute") or ""
    content = skill.get("content") or ""
    power_bonus = extract_power_bonus(content)
    power_multiplier = extract_power_multiplier(content)
    response_multiplier = extract_response_multiplier(content)
    damage_reduction = 0.0

    defender_skill = None
    if defender_skill_name:
        defender_query = normalize_text(defender_skill_name)
        for candidate in df.get("skills", []):
            if defender_query in normalize_text(candidate.get("name") or ""):
                defender_skill = candidate
                break
    if defender_skill and normalize_text(defender_skill.get("skill_type") or "") == "防御":
        damage_reduction = extract_reduction_rate(defender_skill.get("content") or "")

    atk_stats = compute_attr_bounds(atk.get("wikitext_title") or atk.get("name"))
    df_stats = compute_attr_bounds(df.get("wikitext_title") or df.get("name"))
    atk_choice = pick_attr_variant(atk_stats, attacker_state_key)
    df_choice = pick_attr_variant(df_stats, defender_state_key)

    if "物攻" in skill_type or ("物" in skill_type and "防" not in skill_type):
        atk_attr_val = atk_choice.get("物攻", 1)
        df_attr_val = df_choice.get("物防", 1)
    else:
        atk_attr_val = atk_choice.get("魔攻", 1)
        df_attr_val = df_choice.get("魔防", 1)

    attacker_level = (1 + float(attacker_attack_up) + float(defender_defense_down)) / max(
        1e-9, (1 + float(attacker_attack_down) + float(defender_defense_up))
    )

    pet_attrs = get_pet_types(atk)
    stab = 1.25 if skill_attr and skill_attr in pet_attrs else 0.9

    defender_types = get_pet_types(df)
    type_mult = lookup_type_multiplier(counter, defender_types, skill_attr)

    if df_attr_val == 0:
        df_attr_val = 1
    raw = (
        atk_attr_val
        / df_attr_val
        * 0.9
        * ((skill_power * response_multiplier) + power_bonus)
        * attacker_level
        * power_multiplier
        * stab
        * type_mult
        * float(weather)
        * float(combo)
        * (1 - damage_reduction)
    )
    return {
        "attacker": atk.get("wikitext_title") or atk.get("name"),
        "defender": df.get("wikitext_title") or df.get("name"),
        "skill": skill.get("name"),
        "defender_skill": defender_skill.get("name") if defender_skill else None,
        "skill_power": skill_power,
        "power_bonus": power_bonus,
        "power_multiplier": power_multiplier,
        "response_multiplier": response_multiplier,
        "damage_reduction": damage_reduction,
        "attacker_level": attacker_level,
        "atk_attr": atk_attr_val,
        "def_attr": df_attr_val,
        "stab": stab,
        "type_multiplier": type_mult,
        "weather": float(weather),
        "combo": float(combo),
        "estimate": int(max(0, raw)),
    }


def damage_estimate(attacker_name, defender_name, skill_name, **kwargs):
    result = damage_breakdown(attacker_name, defender_name, skill_name, **kwargs)
    return result


def _build_parser():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd")

    sp = sub.add_parser("pet-skills")
    sp.add_argument("name")

    sp = sub.add_parser("skill-learners")
    sp.add_argument("skill")

    sp = sub.add_parser("skill-info")
    sp.add_argument("skill")

    sp = sub.add_parser("pet-info")
    sp.add_argument("name")

    sp = sub.add_parser("pet-attr-bounds")
    sp.add_argument("name")

    sp = sub.add_parser("damage-estimate")
    sp.add_argument("attacker")
    sp.add_argument("defender")
    sp.add_argument("skill")

    return p


def main():
    parser = _build_parser()
    args = parser.parse_args()
    if args.cmd == "pet-skills":
        import pprint
        pprint.pp(pet_skills(args.name))
    elif args.cmd == "skill-learners":
        import pprint
        pprint.pp(pets_by_skill(args.skill))
    elif args.cmd == "skill-info":
        import pprint
        pprint.pp(skill_info(args.skill))
    elif args.cmd == "pet-info":
        import pprint
        pprint.pp(pet_info(args.name))
    elif args.cmd == "pet-attr-bounds":
        import pprint
        pprint.pp(compute_attr_bounds(args.name))
    elif args.cmd == "damage-estimate":
        import pprint
        pprint.pp(damage_estimate(args.attacker, args.defender, args.skill))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
