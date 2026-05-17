const { app, BrowserWindow, screen, ipcMain } = require('electron')
const path = require('path')
const os = require('os')
const fs = require('fs')

const tempRoot = path.join(os.tmpdir(), 'rk-view')
const userDataPath = path.join(tempRoot, 'userData')
const cachePath = path.join(tempRoot, 'cache')
const crashPath = path.join(tempRoot, 'crashDumps')

// Reduce Windows startup noise from GPU / cache / crashpad initialization.
app.disableHardwareAcceleration()

for (const dir of [tempRoot, userDataPath, cachePath, crashPath]) {
  try {
    fs.mkdirSync(dir, { recursive: true })
  } catch (e) {
    // ignore directory creation failures here; Electron will surface real path issues later
  }
}

try {
  // try to redirect paths and reduce noise from crashpad/breakpad
  app.setPath('userData', userDataPath)
  app.setPath('sessionData', cachePath)
  app.setPath('crashDumps', crashPath)
  app.commandLine.appendSwitch('disk-cache-dir', cachePath)
  app.commandLine.appendSwitch('disable-http-cache')
  app.commandLine.appendSwitch('disable-crash-reporter')
  app.commandLine.appendSwitch('disable-breakpad')
  // try to avoid electron attaching console on Windows which prints noisy logs
  process.env.ELECTRON_NO_ATTACH_CONSOLE = '1'
} catch (e) {
  // ignore
}

function createWindow() {
  const display = screen.getPrimaryDisplay()
  const workArea = display.workArea
  // 将面板宽度调整为屏幕宽度的约 1/5，便于显示更宽的导入面板
  const width = Math.max(360, Math.floor(workArea.width / 5))
  const height = workArea.height
  const x = workArea.x + workArea.width - width
  const y = workArea.y

  const win = new BrowserWindow({
    x,
    y,
    width,
    height,
    frame: false,
    transparent: false,
    resizable: false,
    alwaysOnTop: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true
    }
  })

  const isDev = process.env.ELECTRON_DEV === 'true' || process.env.NODE_ENV === 'development'
  if (isDev) {
    win.loadURL('http://localhost:5173')
    win.webContents.once('dom-ready', () => {
      win.webContents.openDevTools({ mode: 'detach' })
    })
  } else {
    const indexPath = path.join(__dirname, 'dist', 'index.html')
    win.loadFile(indexPath)
  }
}

app.whenReady().then(() => {
  createWindow()

  app.on('activate', function () {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('window-all-closed', function () {
  if (process.platform !== 'darwin') app.quit()
})

ipcMain.handle('list-modules', async () => {
  const fs = require('fs')
  const modulesDir = path.join(__dirname, 'modules')
  try {
    const files = await fs.promises.readdir(modulesDir)
    return files.filter(f => f.endsWith('.html'))
  } catch (e) {
    return []
  }
})
