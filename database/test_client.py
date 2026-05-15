import importlib.util
from pathlib import Path

query_path = Path(__file__).parent / "query.py"
spec = importlib.util.spec_from_file_location("db_query", str(query_path))
query = importlib.util.module_from_spec(spec)
spec.loader.exec_module(query)


def run_demo():
    print("Demo: pet-skills 迪莫")
    print(query.pet_skills("迪莫"))

    print("\nDemo: skill-learners 火焰箭")
    print(query.pets_by_skill("火焰箭")[:10])

    print("\nDemo: skill-info 火焰箭")
    print(query.skill_info("火焰箭"))

    print("\nDemo: pet-info 迪莫")
    print(query.pet_info("迪莫"))

    print("\nDemo: pet-attr-bounds 迪莫")
    print(query.compute_attr_bounds("迪莫"))

    print("\nDemo: damage-estimate 迪莫 圣剑骑士 火焰箭")
    print(query.damage_estimate("迪莫", "圣剑骑士", "火焰箭"))


if __name__ == '__main__':
    run_demo()
