#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Quick check on attribute format in pets_detailed.json (including .partial files)"""

import json
import os
import re

# Check both the main file and .partial file
files_to_check = [
    "pvp-helper/data/pets_detailed.json",
    "pvp-helper/data/pets_detailed.json.partial",
]

bad_attributes = {}
good_attributes = set()

for filepath in files_to_check:
    if not os.path.exists(filepath):
        print(f"Skipping {filepath} (not found)")
        continue
    
    print(f"\n=== Checking {filepath} ===")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Failed to load {filepath}: {e}")
        continue
    
    total_pets = len(data)
    total_skills = 0
    bad_count = 0
    good_count = 0
    
    for pet in data:
        for skill in pet.get('skills', []):
            total_skills += 1
            attr = skill.get('attribute', '').strip()
            
            # Check if attribute looks malformed (contains '.png' or full alt text pattern)
            if '.png' in attr or attr.startswith('图标'):
                bad_count += 1
                pet_name = pet.get('title', 'unknown')
                skill_name = skill.get('name', 'unknown')
                if attr not in bad_attributes:
                    bad_attributes[attr] = []
                bad_attributes[attr].append(f"{pet_name} - {skill_name}")
            else:
                if attr:  # non-empty
                    good_count += 1
                    good_attributes.add(attr)

print(f"\n=== Summary ===")
print(f"Total pets: {total_pets}")
print(f"Total skills: {total_skills}")
print(f"Good attributes: {good_count}")
print(f"Bad attributes: {bad_count}")

if bad_attributes:
    print(f"\n=== Malformed Attributes ===")
    for attr, examples in sorted(bad_attributes.items(), key=lambda x: -len(x[1]))[:10]:
        print(f"\n'{attr}' (count: {len(examples)})")
        print(f"  Examples: {examples[:3]}")
else:
    print("\n✓ No malformed attributes found!")

if good_attributes:
    print(f"\n=== Valid Attributes ===")
    print(f"Unique valid attributes ({len(good_attributes)}): {sorted(good_attributes)}")
