import { OverviewModule } from './builtin/OverviewModule'
import { ExampleModule } from './builtin/ExampleModule'

export const builtinModules = [
  {
    id: 'overview',
    title: '总览',
    group: '基础',
    description: '用于展示当前状态、调试入口和后续核心功能的汇总面板。',
    kind: 'component',
    component: OverviewModule
  },
  {
    id: 'example',
    title: '示例模块',
    group: '基础',
    description: '一个占位示例，演示模块如何独立封装自己的内容。',
    kind: 'component',
    component: ExampleModule
  }
]

export function createLegacyHtmlModule(fileName) {
  const id = `legacy:${fileName}`
  const title = fileName.replace(/\.html$/i, '')

  return {
    id,
    title,
    group: 'HTML',
    description: '从 modules 目录加载的旧式 HTML 模块。',
    kind: 'iframe',
    // dev:  http://127.0.0.1:5173/../modules/*.html -> /modules/*.html
    // start: file:///.../dist/index.html -> file:///.../modules/*.html
    src: `../modules/${fileName}`
  }
}
