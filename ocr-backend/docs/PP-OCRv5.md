# 1. 安装接口引擎

三个里面选一个即可

## 安装 transformers 接口引擎
```
python -m pip install "transformers>=5.8.0"
```

## 或安装 paddle_static 接口引擎 GPU 版本
```
python -m pip install paddlepaddle-gpu==3.2.0 -i https://www.paddlepaddle.org.cn/packages/stable/cu126/
```

## 显卡为 NVIDIA 50 系可参考 [官方文档](https://www.paddleocr.ai/latest/en/version3.x/paddlepaddle_installation.html#3-install-paddlepaddle-wheel-packages-for-nvidia-50-series-gpus-on-windows)
```
python -m pip install https://paddle-qa.bj.bcebos.com/paddle-pipeline/Develop-TagBuild-Training-Windows-Gpu-Cuda12.9-Cudnn9.9-Trt10.5-Mkl-Avx-VS2019-SelfBuiltPypiUse/86d658f56ebf3a5a7b2b33ace48f22d10680d311/paddlepaddle_gpu-3.0.0.dev20250717-cp310-cp310-win_amd64.whl
```

# 2. 安装基本包 (OCR only)

```
pip install paddleocr
```

## 3. 下载模型并测试

```
cd ocr-backend/test
python ocr.py
```

## 4. 安装 server 运行依赖

```
pip install uvicorn fastapi python-multipart
```

## 5. 运行 OCR server

在 `ocr-backend` 目录下启动：

```
python -m uvicorn ocr_server:app --host 0.0.0.0 --port 8000 --workers 1
```

## 6. 测试 OCR server

在 `test` 目录下：

```
python client.py
```

预计输出：

```
{'success': True, 'skills': ['幻象', '热砂', '冰爪', '过曝']}
{'success': True, 'skills': ['齿轮扭矩', '齿轮扭矩', '啮合传递', '地刺']}
{'success': True, 'skills': ['地刺', '齿轮扭矩', '啮合传递', '轴承支撑']}
```

顺序与技能所在位置一致，即使传动后也不会有影响。