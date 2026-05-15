# 数据后端（JSON + SQLite + FastAPI）

`database` 目录提供三层能力：

1. 基于 `scraper/data` 的 JSON 查询与伤害计算（`query.py`）
2. SQLite 入库与索引（`db.py`、`db_import.py`、`store.py`）
3. FastAPI 接口服务（`db_server.py`）

---

## 1. 关键操作指令（建议按顺序）

### 1.1 安装依赖

```powershell
cd database
pip install -r requirements.txt
```

### 1.2 （可选）重新生成 `pets_detailed.json`

当你更新了抓取 HTML 或解析逻辑时执行：

```powershell
cd database/scraper
python scraper.py pet-detail --input data\pets_enriched.json --output data\pets_detailed.json --html-dir data\pets_html
```

### 1.3 导入 SQLite（建表 + 建索引 + 入库）

```powershell
cd database
python db_import.py
```

执行后会生成 `database/database.db`，并打印行数统计。

### 1.4 启动 API 服务

```powershell
cd database
python -m uvicorn db_server:app --host 0.0.0.0 --port 8000 --workers 1
```

启动后访问：

- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/docs`

### 1.5 快速自测

```powershell
cd database
python api_client.py
python test_client.py
python db_client.py 迪莫
```

---

## 2. SQLite 说明

### 2.1 当前表结构

- `pets`：宠物主表（名称、属性、资质、特性等）
- `skills`：技能主表（属性、威力、damage、类型、描述）
- `pet_skills`：宠物-技能关系表（含分类、序号）
- `counters`：克制关系 JSON 存档

### 2.2 已建立索引

- `idx_pets_name`
- `idx_pets_wikitext`
- `idx_skills_name`
- `idx_pet_skills_pet`
- `idx_pet_skills_skill`

### 2.3 Python 侧快速检查

```python
import db

conn = db.get_conn()
print(db.count_rows(conn))
conn.close()
```

---

## 3. API 接口列表

### 3.1 宠物与技能查询

- `GET /pets/{name}`：宠物详情（资质、属性、特性、技能数）
- `GET /pets/{name}/skills`：宠物技能池
- `GET /skills/{skill_name}`：技能详情
- `GET /skills/{skill_name}/learners`：学习该技能的宠物列表

### 3.2 属性计算

- `GET /pets/{name}/attr-bounds`

根据 `qualification.stats_map` 输出 4 组属性枚举：

- `iv_low|nature_-0.1`
- `iv_low|nature_+0.2`
- `iv_high|nature_-0.1`
- `iv_high|nature_+0.2`

公式：

- 生命 = [1.7 × 种族值 + 个体值 × 0.85 + 70] × (1 + 性格修正) + 100
- 其他 = [1.1 × 种族值 + 个体值 × 0.55 + 10] × (1 + 性格修正) + 50

### 3.3 伤害计算

- `POST /damage/calculate`

常用字段：

- `attacker_name` / `defender_name`
- `attacker_skill_names` / `defender_skill_names`
- `attacker_state_keys` / `defender_state_keys`
- `attacker_attack_up` / `attacker_attack_down`
- `defender_defense_up` / `defender_defense_down`
- `weather` / `combo`

详细公式：

```text
详细公式 = 进攻方攻击属性值 ÷ 防御方防御属性值 × 0.9 ×（技能威力 × 应对倍率 + 威力加成）× 能力等级 × 威力提升倍数 × 本系加成 × 克制关系 × 天气影响 × 连击数 ×（1 - 减伤率）
```

关键解析规则：

- `技能威力` 优先取 `damage`，缺失回退到 `power`
- `应对倍率`、`威力加成`、`威力提升倍数` 从技能 `content` 文本解析
- `减伤率` 从防守技能文本（如 `减伤70%`）解析
- `克制关系` 来自 `counter_received_damage.json`

---

## 4. 数据来源

数据来自 `database/scraper/data`：

- `pets_detailed.json`
- `counter_received_damage.json`
- `pets_html` 页面缓存
