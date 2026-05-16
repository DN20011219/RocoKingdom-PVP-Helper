# 图片库

作为项目的图片识别素材库，图片库的数据源是有限的。

图片库由如下组件组成：

- icon 。图标库，存储了大量用于图片识别的固定图标。

## 下载脚本

在 `database\pic\icon\download_icons.py` 中可以从 `database\scraper\data\pets_detailed.json` 批量下载图标：

```powershell
cd database\pic\icon
python download_icons.py --target all
```

可选目标：

- `pets`：下载宠物图标到 `pets\`
- `skills`：下载技能图标到 `skills\`
- `all`：同时下载两类图标

状态图标当前还没有整理好的数据源，因此暂不支持自动下载。