const { contextBridge, ipcRenderer } = require('electron')

// debug log so we can confirm preload ran
try {
  // eslint-disable-next-line no-console
  console.log('rk-view preload loaded')
} catch (e) {}

contextBridge.exposeInMainWorld('rkView', {
  listModules: () => ipcRenderer.invoke('list-modules'),
  // small test helper to confirm preload is active
  ping: () => true
})
