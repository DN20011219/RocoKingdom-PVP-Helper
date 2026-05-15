import requests

# 示例结果：{'success': True, 'skills': ['幻象', '热砂', '冰爪', '过曝']}
with open("skills.png", "rb") as f:
    resp = requests.post("http://localhost:8000/skills", files={"file": f})
    print(resp.json())
with open("skills2.png", "rb") as f:
    resp = requests.post("http://localhost:8000/skills", files={"file": f})
    print(resp.json())
with open("skills3.png", "rb") as f:
    resp = requests.post("http://localhost:8000/skills", files={"file": f})
    print(resp.json())


with open("state_enemy.png", "rb") as f:
    resp = requests.post("http://localhost:8000/enemy-hp", files={"file": f})
    print(resp.json())
with open("state_enemy2.png", "rb") as f:
    resp = requests.post("http://localhost:8000/enemy-hp", files={"file": f})
    print(resp.json())


with open("state_self.png", "rb") as f:
    resp = requests.post("http://localhost:8000/self-hp", files={"file": f})
    print(resp.json())
with open("state_self2.png", "rb") as f:
    resp = requests.post("http://localhost:8000/self-hp", files={"file": f})
    print(resp.json())
