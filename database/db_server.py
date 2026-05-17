from __future__ import annotations

import importlib.util
import re
from pathlib import Path
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


def _load_query_module():
    try:
        import query as query_module  # type: ignore
        return query_module
    except Exception:
        query_path = Path(__file__).resolve().parent / "query.py"
        spec = importlib.util.spec_from_file_location("db_query", str(query_path))
        if not spec or not spec.loader:
            raise RuntimeError("Unable to load database/query.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module


def _load_db_module():
    try:
        import db as db_module  # type: ignore
        return db_module
    except Exception:
        db_path = Path(__file__).resolve().parent / "db.py"
        spec = importlib.util.spec_from_file_location("db_store", str(db_path))
        if not spec or not spec.loader:
            raise RuntimeError("Unable to load database/db.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module


query = _load_query_module()
db = _load_db_module()

app = FastAPI(
    title="RocoKingdom Database Service",
    version="1.0.0",
    description="基于 database/scraper/data 的宠物与技能查询服务",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


TEAM_STAT_KEYS = ["生命", "物攻", "魔攻", "物防", "魔防", "速度"]


class DamageRequest(BaseModel):
    attacker_name: str = Field(..., description="攻击方宠物名称")
    defender_name: str = Field(..., description="防御方宠物名称")
    attacker_skill_names: List[str] = Field(default_factory=list, description="攻击方可能使用的技能名称列表")
    defender_skill_names: List[str] = Field(default_factory=list, description="防御方可能使用的技能名称列表")
    attacker_state_keys: List[str] = Field(default_factory=list, description="攻击方属性枚举键列表")
    defender_state_keys: List[str] = Field(default_factory=list, description="防御方属性枚举键列表")
    attacker_attack_up: float = 0.0
    attacker_attack_down: float = 0.0
    defender_defense_up: float = 0.0
    defender_defense_down: float = 0.0
    weather: float = 1.0
    combo: float = 1.0


class TeamImportRequest(BaseModel):
    text: str = Field(..., description="队伍导入文本")


class TeamAttributeRequest(BaseModel):
    hp: int = Field(..., alias="生命", description="生命")
    attack: int = Field(..., alias="物攻", description="物攻")
    defense: int = Field(..., alias="物防", description="物防")
    magic_attack: int = Field(..., alias="魔攻", description="魔攻")
    magic_defense: int = Field(..., alias="魔防", description="魔防")
    speed: int = Field(..., alias="速度", description="速度")


def _open_db_conn():
    conn = db.get_conn()
    db.create_schema(conn)
    return conn


def _parse_team_import_text(text: str):
    raw_text = (text or "").strip()
    if not raw_text:
        raise HTTPException(status_code=400, detail="import text is empty")

    team_name = None
    resonance_magic = None
    members = []

    for raw_line in raw_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        if line.startswith("###") and team_name is None:
            team_name = line.lstrip("#").strip()
            continue

        magic_match = re.match(r"^#\s*魔法[:：]\s*(.+)$", line)
        if magic_match:
            resonance_magic = magic_match.group(1).strip()
            continue

        if not line.startswith("#"):
            continue

        member_match = re.match(r"^#\s*([^：#]+?)\s*：\s*([^、]+?)\s*、\s*\{([^}]*)\}\s*$", line)
        if not member_match:
            continue

        pet_name = member_match.group(1).strip()
        bloodline = member_match.group(2).strip()
        skill_text = member_match.group(3).strip()
        skills = [item.strip() for item in skill_text.split("、") if item.strip()]

        if pet_name and pet_name not in {member["pet_name"] for member in members}:
            base_stats = query.compute_base_attrs(pet_name)
            members.append(
                {
                    "pet_name": pet_name,
                    "bloodline": bloodline,
                    "skills": skills,
                    "stats": base_stats if base_stats else None,
                    "member_index": len(members),
                }
            )

    if not team_name:
        raise HTTPException(status_code=400, detail="team name not found")
    if not resonance_magic:
        raise HTTPException(status_code=400, detail="resonance magic not found")
    if not members:
        raise HTTPException(status_code=400, detail="team members not found")

    return {
        "name": team_name,
        "resonance_magic": resonance_magic,
        "members": members,
        "source_text": raw_text,
    }


@app.get("/health")
def health():
    pets, _ = query.load_data()
    conn = _open_db_conn()
    try:
        rows = db.list_teams(conn)
    finally:
        conn.close()
    return {"ok": True, "pets": len(pets), "teams": len(rows)}


@app.get("/teams")
def list_teams():
    conn = _open_db_conn()
    try:
        teams = db.list_teams(conn)
    finally:
        conn.close()
    return {"teams": teams, "count": len(teams)}


@app.get("/teams/{team_name}")
def get_team(team_name: str):
    conn = _open_db_conn()
    try:
        team = db.get_team_by_name(conn, team_name)
    finally:
        conn.close()
    if not team:
        raise HTTPException(status_code=404, detail="team not found")
    return team


@app.post("/teams/import")
def import_team(payload: TeamImportRequest):
    team_data = _parse_team_import_text(payload.text)
    conn = _open_db_conn()
    try:
        cur = conn.cursor()
        cur.execute("BEGIN")
        team_id = db.upsert_team(conn, team_data["name"], team_data["resonance_magic"], team_data["source_text"])
        db.replace_team_members(conn, team_id, team_data["members"])
        conn.commit()
        team = db.get_team_by_name(conn, team_data["name"])
    except HTTPException:
        conn.rollback()
        raise
    except Exception as exc:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        conn.close()

    return {"success": True, "team": team}


@app.post("/teams/{team_name}/pets/{pet_name}/attributes")
def set_team_member_attributes(team_name: str, pet_name: str, payload: TeamAttributeRequest):
    stats = {
        "生命": payload.hp,
        "物攻": payload.attack,
        "魔攻": payload.magic_attack,
        "物防": payload.defense,
        "魔防": payload.magic_defense,
        "速度": payload.speed,
    }
    conn = _open_db_conn()
    try:
        cur = conn.cursor()
        cur.execute("BEGIN")
        updated = db.set_team_member_stats(conn, team_name, pet_name, stats)
        if not updated:
            conn.rollback()
            raise HTTPException(status_code=404, detail="team member not found")
        conn.commit()
    except HTTPException:
        raise
    except Exception as exc:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        conn.close()

    return {"success": True, "team_name": team_name, "pet_name": pet_name, "stats": stats, "member": updated}


@app.get("/pets/{name}/skills")
def get_pet_skills(name: str):
    skills = query.pet_skills(name)
    if not skills:
        raise HTTPException(status_code=404, detail="pet not found")
    return {"pet": name, "skills": skills}


@app.get("/skills/{skill_name}/learners")
def get_skill_learners(skill_name: str):
    learners = query.pets_by_skill(skill_name)
    return {"skill": skill_name, "pets": learners}


@app.get("/skills/{skill_name}")
def get_skill_info(skill_name: str):
    info = query.skill_info(skill_name)
    if not info:
        raise HTTPException(status_code=404, detail="skill not found")
    return info


@app.get("/pets/{name}")
def get_pet_info(name: str):
    info = query.pet_info(name)
    if not info:
        raise HTTPException(status_code=404, detail="pet not found")
    return info


@app.get("/pets/{name}/attr-bounds")
def get_pet_attr_bounds(name: str):
    bounds = query.compute_attr_bounds(name)
    if not bounds:
        raise HTTPException(status_code=404, detail="pet not found")
    return {"pet": name, "bounds": bounds}


@app.get("/pets/{name}/base-attrs")
def get_pet_base_attrs(name: str):
    attrs = query.compute_base_attrs(name)
    if not attrs:
        raise HTTPException(status_code=404, detail="pet not found")
    return {"pet": name, "base_attrs": attrs}


@app.post("/damage/calculate")
def calculate_damage(payload: DamageRequest):
    pets, _ = query.load_data()
    attacker_matches = query.find_pets(payload.attacker_name, pets)
    defender_matches = query.find_pets(payload.defender_name, pets)
    if not attacker_matches:
        raise HTTPException(status_code=404, detail="attacker not found")
    if not defender_matches:
        raise HTTPException(status_code=404, detail="defender not found")

    attacker_pet = attacker_matches[0]
    defender_pet = defender_matches[0]
    attacker_bounds = query.compute_attr_bounds(attacker_pet.get("wikitext_title") or attacker_pet.get("name"))
    defender_bounds = query.compute_attr_bounds(defender_pet.get("wikitext_title") or defender_pet.get("name"))

    attacker_state_keys = payload.attacker_state_keys or list(attacker_bounds.keys())
    defender_state_keys = payload.defender_state_keys or list(defender_bounds.keys())

    attacker_skill_names = payload.attacker_skill_names or [skill.get("name") for skill in attacker_pet.get("skills", [])]
    defender_skill_names = payload.defender_skill_names or [None]

    results = []
    for attacker_skill_name in attacker_skill_names:
        if not attacker_skill_name:
            continue
        for defender_skill_name in defender_skill_names:
            for attacker_state_key in attacker_state_keys:
                for defender_state_key in defender_state_keys:
                    result = query.damage_breakdown(
                        attacker_pet.get("wikitext_title") or attacker_pet.get("name"),
                        defender_pet.get("wikitext_title") or defender_pet.get("name"),
                        attacker_skill_name,
                        defender_skill_name=defender_skill_name,
                        attacker_state_key=attacker_state_key,
                        defender_state_key=defender_state_key,
                        attacker_attack_up=payload.attacker_attack_up,
                        attacker_attack_down=payload.attacker_attack_down,
                        defender_defense_up=payload.defender_defense_up,
                        defender_defense_down=payload.defender_defense_down,
                        weather=payload.weather,
                        combo=payload.combo,
                    )
                    if result.get("error"):
                        continue
                    result["attacker_state_key"] = attacker_state_key
                    result["defender_state_key"] = defender_state_key
                    result["attacker_skill_name"] = attacker_skill_name
                    result["defender_skill_name"] = defender_skill_name
                    results.append(result)

    return {
        "attacker": attacker_pet.get("wikitext_title") or attacker_pet.get("name"),
        "defender": defender_pet.get("wikitext_title") or defender_pet.get("name"),
        "count": len(results),
        "results": results,
    }


@app.get("/")
def root():
    return {
        "name": "RocoKingdom Database Service",
        "endpoints": [
            "/health",
            "/teams",
            "/teams/import",
            "/teams/{team_name}",
            "/teams/{team_name}/pets/{pet_name}/attributes",
            "/pets/{name}",
            "/pets/{name}/skills",
            "/pets/{name}/attr-bounds",
            "/pets/{name}/base-attrs",
            "/skills/{skill_name}",
            "/skills/{skill_name}/learners",
            "/damage/calculate",
        ],
    }
