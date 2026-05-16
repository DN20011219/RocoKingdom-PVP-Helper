import React from 'react'

export function OverviewModule() {
  return (
    <section className="module-card module-card--hero">
      <div className="module-kicker">核心入口</div>
      <h1>Roco View</h1>
      <p>
        这是一个可替换模块框架。顶部菜单负责选择模块，内容区只负责渲染当前模块，
        后续接入战斗识别、状态面板、宠物信息、技能决策等功能时，只需要新增模块定义即可。
      </p>
      <div className="module-grid">
        <div className="mini-card">
          <div className="mini-card__label">渲染方式</div>
          <div className="mini-card__value">React Component / HTML iframe</div>
        </div>
        <div className="mini-card">
          <div className="mini-card__label">定位</div>
          <div className="mini-card__value">屏幕右侧无边框面板</div>
        </div>
        <div className="mini-card">
          <div className="mini-card__label">扩展方式</div>
          <div className="mini-card__value">新增模块定义，不改布局壳</div>
        </div>
      </div>
    </section>
  )
}
