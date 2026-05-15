# 数据源

技能图标数据源来自 `database\scraper\data\pets_detailed.json` 。

该数据源主要用于以视觉模式匹配使用的技能。

```json
[
  {
    "name": "页面 宠物 立绘 迪莫 1.png",
    "link": "https://wiki.biligame.com/rocom/%E8%BF%AA%E8%8E%AB",
    "art": "https://patchwiki.biligame.com/images/rocom/thumb/2/25/o64cvcxq1l6tlur77xjqbwx2s4imabd.png/180px-%E9%A1%B5%E9%9D%A2_%E5%AE%A0%E7%89%A9_%E7%AB%8B%E7%BB%98_%E8%BF%AA%E8%8E%AB_1.png",
    "art_abs": "https://patchwiki.biligame.com/images/rocom/thumb/2/25/o64cvcxq1l6tlur77xjqbwx2s4imabd.png/180px-%E9%A1%B5%E9%9D%A2_%E5%AE%A0%E7%89%A9_%E7%AB%8B%E7%BB%98_%E8%BF%AA%E8%8E%AB_1.png",
    "attributes": [
      {
        "key": "精灵类型",
        "name": "永远的伙伴"
      },
      {
        "key": "主属性",
        "name": "光"
      }
    ],
    "wikitext_title": "迪莫",
    "html_path": "data\\pets_html\\迪莫.html",
    "skills": [
      {
        "category": "精灵技能",
        "name": "猛烈撞击",
        "icon_title": "猛烈撞击",
        "icon_href": "/rocom/%E7%8C%9B%E7%83%88%E6%92%9E%E5%87%BB",
        "attribute": "普通",
        "level": "LV1 ",
        "power": "1",
        "damage": "65",
        "skill_type": "物攻",
        "content": "✦对敌方精灵造成物理伤害。",
        "index": 0,
        "skill_page": "data\\pets_html\\skills\\猛烈撞击.html"
      },
    ]
  }
]
```

示例数据如上，其中 `icon_href` 字段为技能图标地址，下载的技能图标文件以 "技能名（`name`字段）.png" 命名。

在下载技能图标时，需要注意，每个技能（以技能名称为准）是唯一的，所以只需要下载一份图标文件。

在这个下载过程，可以同步构建后端数据库的技能表。
