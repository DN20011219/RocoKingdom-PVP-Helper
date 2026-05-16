import React from 'react'

export function ModuleHost({ module }) {
  if (!module) {
    return (
      <div className="module-empty">
        <h2>没有可显示的模块</h2>
        <p>请先从上方菜单选择一个模块。</p>
      </div>
    )
  }

  if (module.kind === 'iframe') {
    return <iframe title={module.title} src={module.src} frameBorder="0" />
  }

  const Component = module.component
  return <Component />
}
