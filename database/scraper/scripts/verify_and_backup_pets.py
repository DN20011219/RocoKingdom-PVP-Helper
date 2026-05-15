import json
import os
import shutil
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(ROOT, 'data')
INPUT = os.path.join(DATA_DIR, 'pets_detailed.json')
REPORT = os.path.join(DATA_DIR, 'skill_enrich_report.json')


def load():
    with open(INPUT, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_report(report):
    with open(REPORT, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)


def backup():
    ts = datetime.now().strftime('%Y%m%d-%H%M%S')
    bak = INPUT + f'.bak.{ts}'
    shutil.copy2(INPUT, bak)
    return bak


def main():
    data = load()
    total_pets = len(data) if isinstance(data, list) else len(list(data.keys()))
    total_skills = 0
    with_attr = 0
    with_desc = 0
    with_page = 0
    with_error = 0
    per_pet_missing = []

    for pet in data:
        skills = pet.get('skills', []) if isinstance(pet, dict) else []
        miss = 0
        for s in skills:
            total_skills += 1
            if s.get('attribute'):
                with_attr += 1
            else:
                miss += 1
            if s.get('description'):
                with_desc += 1
            if s.get('skill_page'):
                with_page += 1
            if s.get('skill_page_error') or s.get('skill_enrich_error'):
                with_error += 1
        if miss:
            per_pet_missing.append({'id': pet.get('id') or pet.get('key') or pet.get('name'), 'name': pet.get('name'), 'missing_skills': miss})

    per_pet_missing.sort(key=lambda x: x['missing_skills'], reverse=True)

    report = {
        'total_pets': total_pets,
        'total_skills': total_skills,
        'skills_with_attribute': with_attr,
        'skills_with_description': with_desc,
        'skills_with_skill_page_cached': with_page,
        'skills_with_errors': with_error,
        'pets_with_missing_skills_top10': per_pet_missing[:10],
    }

    bak = backup()
    save_report(report)
    print('Backup created:', bak)
    print('Report written:', REPORT)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
