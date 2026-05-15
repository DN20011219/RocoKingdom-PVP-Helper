from db import get_conn, count_rows
from store import get_pet_by_name, get_skills_for_pet
import sys


def main():
    conn = get_conn()
    print(count_rows(conn))
    if len(sys.argv) > 1:
        pet = sys.argv[1]
        p = get_pet_by_name(conn, pet)
        print(p)
        if p:
            skills = get_skills_for_pet(conn, p["id"])
            print(f"skills: {len(skills)}")
    conn.close()


if __name__ == "__main__":
    main()
