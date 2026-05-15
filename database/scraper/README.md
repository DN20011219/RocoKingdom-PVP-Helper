# 洛克王国 Wiki 爬虫工具 (Roco Kingdom Scraper)

本工具用于从 [洛克王国 Wiki (wiki.biligame.com/rocom)](https://wiki.biligame.com/rocom/) 爬取游戏数据，包括宠物信息、技能数据、克制关系等。

## 一、功能概述

本爬虫提供以下数据爬取功能：

| 命令 | 功能 | 输出文件 |
|------|------|----------|
| `pets` | 从宠物列表页爬取基础宠物信息（名字、链接、图片、属性） | `pets.json` |
| `pet-enrich` | 补充宠物的详细属性信息（从 Wiki 文本模板提取） | `pets_enriched.json` |
| `pet-detail` | 逐只爬取宠物完整详情（资质、特性、技能三池） | `pets_detailed.json` + `pets_html/` |
| `counter-received` | 爬取克制计算器的伤害倍数数据 | `counter_received_damage.json` |

## 二、环境配置

### 2.1 依赖安装

```bash
# 安装依赖（仅需一次）
pip install -r pvp-helper/requirements.txt
```

> **注**: 脚本使用 `urllib`（Python 标准库），无需额外网络库。如果安装了 `requests`，会自动优先使用。

### 2.2 网络配置

- **代理**: 脚本会自动绕过 Windows 系统代理探测，直接访问 Wiki
- **超时**: 默认单次请求超时 15-30 秒
- **重试**: 网络错误会自动重试最多 3 次（指数退避）

## 三、定期更新流程

### 3.1 快速更新（仅更新宠物详情）

如果只想更新已有宠物的详细数据（资质、特性、技能），使用以下命令：

```bash
cd database\scraper
python scraper.py pet-detail `
  --input data\pets_enriched.json `
  --output data\pets_detailed.json `
  --html-dir data\pets_html
```

**优势**: 
- 会自动检测已下载的 HTML，跳过重复下载
- 会自动读取已生成的 `pets_detailed.json`，只补充缺失的宠物
- 断点续传：可以中断后重新运行，自动从上次中断位置继续

**预计耗时**: 514 只宠物 × 15-30 秒/只 ≈ 2-4 小时

### 3.2 完整重新爬取（更新所有数据）

如果需要从零开始重新爬取（比如 Wiki 大幅更新）：

```bash
cd RocoKingdom-World

# 第 1 步：爬取宠物列表
python scraper.py pets `
  https://wiki.biligame.com/rocom/%E5%AE%A0%E7%89%A9%E5%88%97%E8%A1%A8 `
  --outdir data

# 第 2 步：补充属性信息
python scraper.py pet-enrich `
  --input data\pets.json `
  --output data\pets_enriched.json

# 第 3 步：爬取每只宠物详情（耗时最长）
python scraper.py pet-detail `
  --input data\pets_enriched.json `
  --output data\pets_detailed.json `
  --html-dir data\pets_html

# 第 4 步：爬取克制计算器数据
python scraper.py counter-received `
  https://wiki.biligame.com/rocom/%E5%85%8B%E5%88%B6%E8%AE%A1%E7%AE%97%E5%99%A8 `
  --output data\counter_received_damage.json
```

**预计耗时**: 
- pets: 1 分钟
- pet-enrich: 3-5 分钟
- pet-detail: 2-4 小时
- counter-received: 1 分钟

## 四、数据文件说明

### pets.json

**内容**: 宠物基础信息（从列表页爬取）

**结构**:
```json
[
  {
    "name": "迪莫",
    "link": "https://wiki.biligame.com/rocom/迪莫",
    "art": "/rocom/images/...",
    "art_abs": "https://wiki.biligame.com/rocom/images/...",
    "attributes": [
      {"name": "属性 龙.png", "src": "...", "src_abs": "..."}
    ]
  }
]
```

### pets_enriched.json

**内容**: 宠物基础信息 + 从 Wiki 文本模板提取的完整属性

**新增字段**:
- `attributes`: 更新为完整的属性列表
- `wikitext_title`: Wiki 页面标题（用于 pet-detail 参考）

### pets_detailed.json

**内容**: 完整宠物详情（514 只）

**核心字段**:
- `html_path`: 本地缓存的 HTML 文件路径
- `qualification`: 
  - `total`: 总资质
  - `stats`: 数组格式，包含 [生命, 物攻, 魔攻, 物防, 魔防, 速度]
  - `stats_map`: Key-Value 格式，例 `{"生命": "120", "物攻": "80", ...}`
- `characteristic`: 
  - `name`: 特性名称
  - `content`: 特性效果描述
- `skill_pools`: 技能按类型分组 (精灵技能 / 血脉技能 / 可学技能石)
- `skills`: 扁平的完整技能列表
- `error`: 若爬取失败，此字段记录错误信息；否则为空

**示例**:
```json
{
  "name": "迪莫",
  "link": "...",
  "wikitext_title": "迪莫",
  "qualification": {
    "total": "738",
    "stats": [
      {"name": "生命", "value": "120"},
      {"name": "物攻", "value": "80"},
      ...
    ],
    "stats_map": {
      "生命": "120",
      "物攻": "80",
      ...
    }
  },
  "characteristic": {
    "name": "最好的伙伴",
    "content": "造成克制伤害后，获得..."
  },
  "skill_pools": [
    {
      "category": "精灵技能",
      "skills": [...]
    },
    {
      "category": "血脉技能",
      "skills": [...]
    },
    {
      "category": "可学技能石",
      "skills": [...]
    }
  ],
  "error": ""
}
```

### counter_received_damage.json

**内容**: 克制计算器的伤害倍数关系

**结构**:
- `single_type_rules`: 单属性防守规则（18 条）
- `dual_type_rules`: 双属性防守规则（306 条，包含所有有序主副系组合）

**字段说明**:
- `defender_type` / `defender_types`: 防守方属性（单/双）
- `received_damage_increased`: 受到伤害增加的属性与倍数
- `received_damage_decreased`: 受到伤害降低的属性与倍数

**示例**:
```json
{
  "single_type_rules": [
    {
      "defender_type": "普通",
      "received_damage_increased": [{"type": "武", "multiplier": "2.0"}],
      "received_damage_decreased": [{"type": "幽", "multiplier": "0.5"}]
    }
  ],
  "dual_type_rules": [
    {
      "defender_types": ["普通", "草"],
      "received_damage_increased": [
        {"type": "武", "multiplier": "2.0"},
        {"type": "火", "multiplier": "2.0"},
        ...
      ],
      "received_damage_decreased": [
        {"type": "幽", "multiplier": "0.5"},
        ...
      ]
    }
  ]
}
```

### pets_html/

**内容**: 本地缓存的宠物 Wiki 页面 HTML（每个宠物一个文件）

**用途**: 
- 避免重复下载
- pet-detail 命令可重复使用不重新下载
- 保留原始 HTML 便于二次解析

## 五、常见用法

### 5.1 只更新特定宠物

```bash
python scraper.py pet-detail `
  --input data\pets_enriched.json `
  --output data\pets_detailed.json `
  --html-dir data\pets_html `
  --only-query 迪莫 `
  --limit 1
```

**参数说明**:
- `--only-query`: 过滤宠物名称或标题包含此字符串的宠物
- `--limit`: 只处理前 N 只匹配的宠物

### 5.2 增量更新（跳过已处理）

直接运行 pet-detail，脚本会：
1. 读取现有的 `pets_detailed.json`
2. 检查缺失的宠物
3. 只爬取缺失的宠物
4. 原子写入结果（不会中断时丢失已处理数据）

```bash
python scraper.py pet-detail `
  --input data\pets_enriched.json `
  --output data\pets_detailed.json `
  --html-dir data\pets_html
```

## 六、可靠性说明

### 6.1 断点续传

- **pet-detail**: 支持中途中断后重新运行，自动从上次停止位置继续
- **pet-enrich**: 支持增量更新（每批 10 只后落盘）

### 6.2 错误处理

- 单个宠物爬取失败不会停止整个批处理，失败信息记录在 `error` 字段
- 网络超时自动重试最多 3 次（2s → 4s → 8s 指数退避）
- Windows 代理问题已解决（绕过系统代理探测）

### 6.3 原子写入

- JSON 输出采用临时文件 + 原子替换，避免中断时文件损坏
- 若 Windows 文件锁定导致覆盖失败，会保存到 `.partial` 文件

## 七、故障排查

### 7.1 网络错误

```
urllib.error.HTTPError: HTTP Error 567: Unknown Status
```

**原因**: Wiki 反爬虫限制

**解决**: 脚本已配置浏览器级别 User-Agent 和请求头，通常会自动通过。若仍然失败：
- 等待 1 小时后重试
- 增加 timeout 参数（如需自定义，修改 scraper.py 中的 `fetch()` 函数）

### 7.2 数据不完整

若 `pets_detailed.json` 仅有部分宠物，检查：

```bash
python -c "import json; data = json.load(open('pvp-helper/data/pets_detailed.json', encoding='utf-8')); print(f'Total pets: {len(data)}')"
```

如果 < 514，继续运行 pet-detail 完成剩余宠物：

```bash
python scraper.py pet-detail `
  --input data\pets_enriched.json `
  --output data\pets_detailed.json `
  --html-dir data\pets_html
```

## 八、文件更新策略

推荐定期更新流程：

1. **每天**: 运行 `pet-detail` 更新宠物详情和技能
2. **每周**: 运行 `pet-enrich` + `pet-detail` 重新爬取属性
3. **赛季**: 运行完整爬取流程，清空 `pets_html/` 后重新下载

## 九、许可和合规

本工具仅用于个人学习和数据分析用途。使用前请：
- 确认符合 Wiki 站点的爬虫政策
- 避免高频重复请求导致服务器压力
- 尊重 Wiki 内容的著作权

再次感谢 [洛克王国 Wiki (wiki.biligame.com/rocom)](https://wiki.biligame.com/rocom/) 提供的详细全面的宠物数据。

## 十、支持的系统

- Windows 10+ (PowerShell 5.0+)
- Python 3.8+
- 需要互联网连接

## 十一、更新历史

- **v1.0** (2026-05-12): 
  - 实现 pets, pet-enrich, pet-detail 命令
  - 实现 counter-received 命令
  - 支持断点续传和增量更新
  - 514 只宠物完整数据爬取
