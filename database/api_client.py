import json
from urllib import request


BASE_URL = "http://127.0.0.1:8000"


def get(path):
    with request.urlopen(f"{BASE_URL}{path}", timeout=15) as resp:
        return json.load(resp)


def post(path, payload):
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(
        f"{BASE_URL}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def main():
    print("health:", get("/health"))
    print("pet info:", get("/pets/%E8%BF%AA%E8%8E%AB"))
    print("pet skills count:", len(get("/pets/%E8%BF%AA%E8%8E%AB/skills").get("skills", [])))
    print("skill info:", get("/skills/%E7%81%AB%E7%84%B0%E7%AE%AD"))
    print("learners:", get("/skills/%E7%81%AB%E7%84%B0%E7%AE%AD/learners").get("pets", [])[:5])
    print(
        "damage:",
        post(
            "/damage/calculate",
            {
                "attacker_name": "迪莫",
                "defender_name": "圣剑骑士",
                "attacker_skill_names": ["火焰箭"],
                "defender_skill_names": [],
                "attacker_state_keys": ["iv_high|nature_+0.2"],
                "defender_state_keys": ["iv_high|nature_+0.2"],
                "weather": 1.0,
                "combo": 1.0,
            },
        ),
    )


if __name__ == "__main__":
    main()
