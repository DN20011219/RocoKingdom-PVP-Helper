# OCR 后端

OCR 能力是分析能力的基础，本文档提供了 OCR 后端的依赖安装、运行、测试相关内容。

## 1. 依赖模型安装

详情阅读 [PP-OCRv5](.\docs\PP-OCRv5.md)

## 2. 启动识别后端

```powershell
cd ocr-backend
python -m uvicorn ocr_server:app --host 0.0.0.0 --port 8000 --workers 1
```

## 3. 测试识别后端

```
cd ocr-backend\test
python client.py
```

