import json
import os
import sys
from urllib.parse import urljoin

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)

import scraper as s


def main():
    with open('pvp-helper/data/pets_enriched.json', encoding='utf-8') as f:
        pets = json.load(f)

    pet = pets[0]
    page = s.download_and_parse_pet_page(pet, 'pvp-helper/data/pets_html')
    print('pet:', pet.get('name'))
    print('first_skill:', page['skills'][0].get('name'))
    print('icon_href:', page['skills'][0].get('icon_href'))

    href = page['skills'][0].get('icon_href')
    if not href:
        print('no href on first skill')
        return

    skill_url = href if href.startswith('http') else urljoin('https://wiki.biligame.com', href)
    html = s.fetch(skill_url, timeout=20)
    print('skill_url:', skill_url)
    print('parsed:', s.parse_skill_detail_from_html(html))


if __name__ == '__main__':
    main()
