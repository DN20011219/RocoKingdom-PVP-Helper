# 数据源

宠物图标数据源来自 `database\scraper\data\pets_detailed.json` 。

该数据源主要用于以视觉模式匹配出场宠物。

可使用 `database\pic\icon\download_icons.py --target pets` 批量下载到当前目录。

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
  }
]
```

示例数据如上，其中 `wikitext_title` 字段为宠物名，下载的宠物图标文件链接为 `art` 字段，文件以 "宠物名.png" 命名。
