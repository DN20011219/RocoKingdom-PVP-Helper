from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import List

from fastapi import FastAPI, HTTPException
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


query = _load_query_module()

app = FastAPI(
    title="RocoKingdom Database Service",
    version="1.0.0",
    description="基于 database/scraper/data 的宠物与技能查询服务",
)


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


@app.get("/health")
def health():
    pets, _ = query.load_data()
    return {"ok": True, "pets": len(pets)}


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
            "/pets/{name}",
            "/pets/{name}/skills",
            "/pets/{name}/attr-bounds",
            "/skills/{skill_name}",
            "/skills/{skill_name}/learners",
            "/damage/calculate",
        ],
    }
