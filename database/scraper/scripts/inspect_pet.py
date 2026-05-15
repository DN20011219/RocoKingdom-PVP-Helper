import json

with open('pvp-helper/data/pets_detailed.json', encoding='utf-8') as f:
    data = json.load(f)

print('Total entries:', len(data))
for i, pet in enumerate(data[:20]):
    print(i, pet.get('name') or pet.get('title') or pet.get('key'))

for pet in data:
    if pet.get('name') and '迪莫' in pet.get('name'):
        print('\nFound', pet.get('name'))
        for s in pet.get('skills', [])[:20]:
            keys = ['name','icon_href','icon_title','attribute','description','skill_page','skill_page_error','skill_enrich_error']
            d = {k: s.get(k) for k in keys}
            print(d)
        break
else:
    print('\n迪莫 not found in names; searching titles...')
    for pet in data:
        if pet.get('title') and '迪莫' in pet.get('title'):
            print('\nFound by title', pet.get('title'))
            for s in pet.get('skills', [])[:20]:
                keys = ['name','icon_href','icon_title','attribute','description','skill_page','skill_page_error','skill_enrich_error']
                d = {k: s.get(k) for k in keys}
                print(d)
            break
    else:
        print('\nStill not found')
