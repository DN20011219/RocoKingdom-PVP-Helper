# 洛克王国：世界 - Vision

本项目致力于为洛克王国世界提供稳定的图像识别功能，以支持其它上层的智能设施。

## 整体架构

项目主要由几个模块构成，分别为

- 负责总体逻辑调用的 `core`
- 提供图像源的 `capture` 
- 提供文本识别能力的 `ocr-backend` 
- 提供视觉匹配能力的 `vision-backend`
- 提供与游戏交互能力的 `interact`
- 存储底层数据的 `database`

`core` 模块是系统的核心部分，它存储了多种分析模式要做的事情。比如战斗页面识别需要完成：识别区域划分，截取对应图片，内容识别（文本识别与图像匹配），数据组装，等任务。

`capture` 模块，根据传入的指令，自适应地截取游戏中的图片，将其缓存并返回给 `core` 组件。如：截取战斗页面的技能列表。 

`ocr-backend` 模块根据传入的指令，解析图片的文字内容，返回给 `core` 组件。如：识别战斗页面的技能列表，识别**印记**或**状态**层数。

`vision-backend` 模块根据传入的指令，以视觉匹配方案匹配图片的内容，返回给 `core` 组件。如：通过我方精灵头像识别精灵，识别**印记**，**状态**。

`interact` 模块提供了若干游戏控制 API ，它封装了人类化操作等复杂内容，将简单的控制指令接口提供给上层应用。如：类人移动，类人点击。`interact` 模块的底层控制基于 [Interception](https://github.com/oblitum/Interception) 实现。

`database` 模块为本项目的数据源。它会定期爬取 [洛克王国 Wiki](https://wiki.biligame.com/rocom/) 的各类数据，以供项目使用。在此基础上，它通过轻量化嵌入式关系数据库 SQLite ，编写了多个查询接口，供上层决策使用。




## 鸣谢

- [洛克王国 Wiki](https://wiki.biligame.com/rocom/) ：本项目的宠物数据均来自 **洛克王国 Wiki**

- [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) ：本项目的 OCR 识别均使用 PaddleOCR 模型

- [Interception](https://github.com/oblitum/Interception) ：本项目的指令控制均使用 Interception 