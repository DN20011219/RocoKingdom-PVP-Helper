from db import get_conn


def get_pet_by_name(conn, name):
    cur = conn.cursor()
    cur.execute("SELECT * FROM pets WHERE name = ? OR wikitext_title = ? LIMIT 1", (name, name))
    row = cur.fetchone()
    return dict(row) if row else None


def get_skills_for_pet(conn, pet_id):
    cur = conn.cursor()
    cur.execute(
        "SELECT s.*, ps.category, ps.skill_index FROM skills s JOIN pet_skills ps ON s.id = ps.skill_id WHERE ps.pet_id = ? ORDER BY ps.skill_index",
        (pet_id,),
    )
    return [dict(r) for r in cur.fetchall()]


def find_pets_by_skill(conn, skill_name):
    cur = conn.cursor()
    cur.execute(
        "SELECT p.* FROM pets p JOIN pet_skills ps ON p.id = ps.pet_id JOIN skills s ON s.id = ps.skill_id WHERE s.name = ?",
        (skill_name,),
    )
    return [dict(r) for r in cur.fetchall()]
