import json
from pathlib import Path
from db import get_conn, create_schema, insert_pet, insert_skill, insert_pet_skill, upsert_counter, DB_PATH


BASE = Path(__file__).resolve().parent
DATA_DIR = BASE / "scraper" / "data"
PETS_FILE = DATA_DIR / "pets_detailed.json"
COUNTERS_FILE = DATA_DIR / "counter_received_damage.json"


def load_json(p: Path):
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def import_all(db_path: Path = DB_PATH):
    conn = get_conn(db_path)
    create_schema(conn)
    pets = load_json(PETS_FILE)
    counters = load_json(COUNTERS_FILE)

    cur = conn.cursor()
    try:
        cur.execute("BEGIN")
        for i, pet in enumerate(pets):
            pet_id = insert_pet(conn, pet)
            # skills is a list of skill objects; each has a 'category' and 'index'
            for skill in pet.get("skills", []) or []:
                cat = skill.get("category")
                idx = skill.get("index") if skill.get("index") is not None else 0
                sid = insert_skill(conn, skill)
                insert_pet_skill(conn, pet_id, sid, cat, idx)

        upsert_counter(conn, "counter_received_damage", counters)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    import sys

    db_file = DB_PATH
    if len(sys.argv) > 1:
        db_file = Path(sys.argv[1])
    print(f"Importing into {db_file}")
    import_all(db_file)
    conn = get_conn(db_file)
    from db import count_rows

    print(count_rows(conn))
    conn.close()
