import React, { useEffect, useMemo, useState } from 'react'
import { ModuleMenu } from './components/ModuleMenu'
import { ModuleHost } from './components/ModuleHost'
import { builtinModules, createLegacyHtmlModule } from './modules/registry'

function groupModules(modules) {
  const map = new Map()

  for (const module of modules) {
    const groupName = module.group || '其他'
    const list = map.get(groupName) || []
    list.push(module)
    map.set(groupName, list)
  }

  return Array.from(map.entries()).map(([name, items]) => ({ name, items }))
}

export default function App() {
  const [legacyModules, setLegacyModules] = useState([])
  const [activeId, setActiveId] = useState('overview')

  useEffect(() => {
    const load = async () => {
      try {
        const list = window.rkView && window.rkView.listModules ? await window.rkView.listModules() : []
        setLegacyModules((list || []).map(createLegacyHtmlModule))
      } catch (error) {
        setLegacyModules([])
      }
    }

    load()
  }, [])

  const modules = useMemo(() => [...builtinModules, ...legacyModules], [legacyModules])
  const activeModule = modules.find(module => module.id === activeId) || modules[0] || null
  const groupedModules = useMemo(() => groupModules(modules), [modules])

  useEffect(() => {
    if (modules.length && !modules.some(module => module.id === activeId)) {
      setActiveId(modules[0].id)
    }
  }, [modules, activeId])

  return (
    <div className="app-root">
      <header className="topbar">
        <div className="title-block">
          <div className="title">Roco View</div>
          <div className="subtitle">可替换模块壳</div>
        </div>
        <ModuleMenu groups={groupedModules} activeId={activeId} onSelect={setActiveId} />
      </header>
      <main className="content">
        <div className="content-shell">
          <ModuleHost module={activeModule} />
        </div>
      </main>
    </div>
  )
}
