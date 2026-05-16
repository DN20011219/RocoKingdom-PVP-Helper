import React from 'react'

export function ExampleModule() {
  return (
    <section className="module-card">
      <div className="module-kicker">示例模块</div>
      <h2>独立模块内容</h2>
      <p>
        这里是一个完全独立的 React 模块。你可以把每个业务能力都拆成一个模块，
        例如战斗状态、宠物详情、技能列表、OCR 结果、视觉识别结果等。
      </p>
      <ul className="module-list-block">
        <li>模块内部可以独立管理状态、请求和交互。</li>
        <li>菜单壳无需知道模块内部细节。</li>
        <li>后续可以把模块进一步拆成更细的子组件。</li>
      </ul>
    </section>
  )
}
