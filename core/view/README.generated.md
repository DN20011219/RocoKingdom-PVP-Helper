快速说明 — core/view 可视化前端

开发启动: 在 `core/view` 目录下执行一条命令即可:

```powershell
cd core\view
npm install
npm run dev
```

`npm run dev` 会同时启动 Vite 和 Electron：

- Vite 监听 `http://127.0.0.1:5173`
- Electron 等待页面就绪后再打开右侧无边框窗口

如果你要启动构建后的生产窗口，再用：

```powershell
npm run start
```

`npm run start` 会先构建 React，再启动 Electron，从 `dist` 里读取相对资源，不依赖 Vite dev server。

如果 `npm run start` 提示正在下载 Electron binary，先执行:

```powershell
npm run electron:download:cn
```

这会从国内镜像下载 Electron 二进制，适合当前网络直连 GitHub 失败的情况。

- 功能:
  - 使用 Electron 启动一个无边框窗口，固定在屏幕右侧，宽度为屏幕的 1/6，默认不可调整大小。
  - 顶部为菜单区域，列出 `modules` 目录下的 HTML 模块。内容区通过 `iframe` 加载模块。

- 扩展模块:
  - 把自定义页面放进 `core/view/modules/` （.html），程序会自动列出并加载。当前 legacy HTML 模块会通过 `../modules/*.html` 访问，所以不要放到 `dist/modules/`。

如需打包 Windows 可执行文件，安装 `electron-packager` 后执行 `npm run pack-win`。
