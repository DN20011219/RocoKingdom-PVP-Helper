import sqlite3
from pathlib import Path
import json
from typing import Optional


DB_PATH = Path(__file__).resolve().parent / "database.db"


def get_conn(path: Optional[Path] = None):
    p = path or DB_PATH
    conn = sqlite3.connect(str(p))
    conn.row_factory = sqlite3.Row
    return conn


def create_schema(conn: sqlite3.Connection):
    cur = conn.cursor()
    cur.executescript(
        """
    PRAGMA journal_mode=WAL;
    CREATE TABLE IF NOT EXISTS pets (
        id INTEGER PRIMARY KEY,
        wikitext_title TEXT,
        name TEXT,
        html_path TEXT,
        attributes TEXT,
        qualification TEXT,
        characteristic TEXT
    );

    CREATE TABLE IF NOT EXISTS skills (
        id INTEGER PRIMARY KEY,
        name TEXT,
        attribute TEXT,
        level TEXT,
        power TEXT,
        damage TEXT,
        skill_type TEXT,
        content TEXT,
        skill_page TEXT
    );

    CREATE TABLE IF NOT EXISTS pet_skills (
        pet_id INTEGER,
        skill_id INTEGER,
        category TEXT,
        skill_index INTEGER,
        UNIQUE(pet_id, skill_id, skill_index)
    );

    CREATE TABLE IF NOT EXISTS counters (
        id INTEGER PRIMARY KEY,
        name TEXT,
        data TEXT
    );

    CREATE INDEX IF NOT EXISTS idx_pets_name ON pets(name);
    CREATE INDEX IF NOT EXISTS idx_pets_wikitext ON pets(wikitext_title);
    CREATE INDEX IF NOT EXISTS idx_skills_name ON skills(name);
    CREATE INDEX IF NOT EXISTS idx_pet_skills_pet ON pet_skills(pet_id);
    CREATE INDEX IF NOT EXISTS idx_pet_skills_skill ON pet_skills(skill_id);
    """
    )
    conn.commit()


def insert_pet(conn: sqlite3.Connection, pet: dict) -> int:
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO pets (wikitext_title, name, html_path, attributes, qualification, characteristic) VALUES (?, ?, ?, ?, ?, ?)",
        (
            pet.get("wikitext_title"),
            pet.get("name"),
            pet.get("html_path"),
            json.dumps(pet.get("attributes", []), ensure_ascii=False),
            json.dumps(pet.get("qualification", {}), ensure_ascii=False),
            json.dumps(pet.get("characteristic", {}), ensure_ascii=False),
        ),
    )
    return cur.lastrowid


def find_skill(conn: sqlite3.Connection, name: str, attribute: str, level: str) -> Optional[int]:
    cur = conn.cursor()
    cur.execute(
        "SELECT id FROM skills WHERE name = ? AND attribute = ? AND level = ? LIMIT 1",
        (name, attribute, level),
    )
    row = cur.fetchone()
    return row["id"] if row else None


def insert_skill(conn: sqlite3.Connection, skill: dict) -> int:
    cur = conn.cursor()
    sid = find_skill(conn, skill.get("name"), skill.get("attribute"), skill.get("level"))
    if sid:
        return sid
    cur.execute(
        "INSERT INTO skills (name, attribute, level, power, damage, skill_type, content, skill_page) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            skill.get("name"),
            skill.get("attribute"),
            skill.get("level"),
            skill.get("power"),
            skill.get("damage"),
            skill.get("skill_type"),
            skill.get("content"),
            skill.get("skill_page"),
        ),
    )
    return cur.lastrowid


def insert_pet_skill(conn: sqlite3.Connection, pet_id: int, skill_id: int, category: str, index: int):
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT OR IGNORE INTO pet_skills (pet_id, skill_id, category, skill_index) VALUES (?, ?, ?, ?)",
            (pet_id, skill_id, category, index),
        )
    except Exception:
        pass


def upsert_counter(conn: sqlite3.Connection, name: str, data: dict):
    cur = conn.cursor()
    cur.execute("DELETE FROM counters WHERE name = ?", (name,))
    cur.execute("INSERT INTO counters (name, data) VALUES (?, ?)", (name, json.dumps(data, ensure_ascii=False)))


def count_rows(conn: sqlite3.Connection):
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as c FROM pets")
    pets = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) as c FROM skills")
    skills = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) as c FROM pet_skills")
    mappings = cur.fetchone()[0]
    return {"pets": pets, "skills": skills, "pet_skills": mappings}
