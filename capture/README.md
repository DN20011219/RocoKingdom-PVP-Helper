# 图像捕获后端

主要功能：在启动时，选择一个应用程序（即游戏界面区域），固定地截取游戏对应位置对应大小的图片，这个位置和大小是由用户编辑的指令控制的。在启动时可以给用户几个实例选择，根据游戏界面的相对位置截取。

需要提供配置管理功能，也就是一个指令：比如截取技能栏，会固定地截取游戏某个位置的一张图片；截取自己宠物，会固定地截取另一个位置的图片。

## 1. 依赖安装
在 `capture` 目录下创建并激活 Python 虚拟环境，然后安装依赖：

```powershell
cd capture
pip install -r requirements.txt
```
## 2. 启动捕获后端

```powershell
cd capture

```

示例运行：

```powershell
python capture_server.py --config config_example.json --interval 1.0 --output captures
```

也可以使用配置管理命令（推荐）：

```powershell
# 初始化配置库
python capture_server.py config init --file capture_profiles.json

# 添加技能栏截图配置（示例）
python capture_server.py config add skill_bar --file capture_profiles.json --mode relative --window-title "Roco Kingdom" --window-exe "NRC-Win64-Shipping.exe" --x 100 --y 200 --width 300 --height 120

# 添加自己宠物截图配置（示例）
python capture_server.py config add self_pet --file capture_profiles.json --mode relative --window-title "Roco Kingdom" --window-exe "NRC-Win64-Shipping.exe" --x 50 --y 450 --width 220 --height 180

# 查看配置
python capture_server.py config list --file capture_profiles.json
python capture_server.py config show skill_bar --file capture_profiles.json

# 按配置名运行
python capture_server.py run --profile skill_bar --profiles-file capture_profiles.json --interval 1.0 --output captures

# 交互式新增配置（选窗口 + 鼠标框选区域）
python capture_server.py config interactive-add skill_bar --file capture_profiles.json --mode relative

# 若已知进程名，可直接按 exe 找窗口（无需依赖窗口标题）
python capture_server.py config interactive-add skill_bar --file capture_profiles.json --mode relative --window-exe "NRC-Win64-Shipping.exe"

# 某些机器切前台较慢时，可增加等待时间
python capture_server.py config interactive-add skill_bar --file capture_profiles.json --mode relative --window-exe "NRC-Win64-Shipping.exe" --focus-delay 0.8

# 开启实时预览窗口（每次抓图刷新，interval=1.0 即每秒刷新）
python capture_server.py run --profile skill_bar --profiles-file capture_profiles.json --interval 1.0 --output captures --preview
```

## 3. 测试捕获后端

```
cd capture
```

测试说明：
- 推荐直接在 `config_example.json` 里使用 `window_exe: NRC-Win64-Shipping.exe` 按进程名定位窗口（更稳定）。
- 也可以设置 `window_title` 按标题匹配，或将 `mode` 改为 `absolute` 并设置 `region` 的绝对坐标（屏幕坐标）。
- 启动脚本后，`captures` 目录会生成按时间戳命名的截图文件。

最小测试流程（建议）：
1. 先用 `config add` 新建一个很小区域（例如 `100x100`）。
2. 执行 `run --profile ...` 跑 2-3 秒。
3. 在 `captures` 目录确认是否有新图片。

交互式流程说明：
1. 执行 `config interactive-add`。
2. 终端里选择窗口序号。
3. 程序会尝试把目标窗口切到前台；若系统拦截，会提示 warning，这时手动点一下游戏窗口即可。
4. 屏幕截图界面中按住鼠标左键拖拽框选区域。
5. 按回车确认（`Esc` 取消）。
6. 使用 `run --profile` 启动抓图。

如果仍未置前：
- 在命令里加 `--focus-delay 0.8` 或 `--focus-delay 1.0`。
- 确保游戏窗口不是管理员权限运行（或让本脚本同样以管理员运行），否则 Windows 可能阻止前台切换。

实时预览说明：
- 使用 `run ... --preview` 启动后，会弹出预览窗口。
- 预览内容是当前框选区域的实时截图。
- 刷新频率由 `--interval` 控制（例如 `1.0` 即约每秒一次）。
- 预览窗口底部会显示当前区域坐标和尺寸：`x, y, w, h`。
- 在预览窗口按 `R` 可以重新框选区域；在框选界面按回车确认、按 `Esc` 取消。

如果需要我可以进一步：
- 添加基于按键的启停控制
- 将截图通过 HTTP 提供为接口
