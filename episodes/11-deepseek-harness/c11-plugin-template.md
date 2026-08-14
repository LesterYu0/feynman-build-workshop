# 10 行插件骨架模板（C11 置顶资产 2/5）

> 给 dsh 加第一个工具的最简模板。**抄走就能用**。90% 的 dsh 插件都是这个骨架。

## scratch-plugin/cordis.yml（挂载配置）

```yaml
# 给 web profile 加一个插件：scratch-plugin
$schema: ./dsh-base/cordis.config.schema.json
include:
  - $id: scratch-plugin
    config: {}
```

## scratch-plugin/package.json

```json
{
  "name": "scratch-plugin",
  "private": true,
  "type": "module",
  "dependencies": {
    "@deepseek-ai/dsh-tools": "workspace:^"
  }
}
```

## scratch-plugin/src/my-plugin.ts（10 行插件核心）

```ts
import { defineTool } from '@deepseek-ai/dsh-tools'

export const name = 'greet-tool'
export const inject = ['tools']

export function apply(ctx) {
  ctx.tools.register(defineTool({
    name: 'greet',
    description: 'Greet someone by name.',
    parameters: {
      name: { type: 'string', required: true, description: 'The name to greet' },
    },
    output: {
      schema: { type: 'string' },
      render: (_args, value) => [{ type: 'text', text: value }],
    },
    async execute(args) {
      return `Hello, ${args.name}!`
    },
  }))
}
```

## 启动 + 验证

```sh
# 启动 web profile 并挂载插件
pnpm dsh web --patch ./scratch-plugin/cordis.yml

# 浏览器打开 http://127.0.0.1:3080
# 在 Web UI 里问模型：
#   "Use the greet tool to greet Ada."
# 模型会自己调用 greet，返回：Hello, Ada!
```

---

## 4 个概念（10 秒读懂）

| 概念 | 作用 |
|---|---|
| `name` | 插件标识，**唯一** |
| `inject` | 声明依赖：`['tools']` 等 Cordis 加载完成后再启动 |
| `apply(ctx)` | 注册入口：`ctx.tools.register` / `ctx.llm` / ... |
| `defineTool` | dsh 提供的工具定义助手，自动校验 schema |

## 5 行→任何工具

工具 = 把这个模板的 `execute()` 换成你的逻辑：

```ts
async execute(args) {
  // 你想做的事
  // - args.path 读文件 → readFile()
  // - args.cmd 跑命令 → spawn
  // - args.url 抓网页 → fetch
  return result
}
```

## 7 个 ctx 服务（不同类型工具挂不同的 ctx）

| 想做什么 | 注册到 |
|---|---|
| 加模型工具 | `ctx.tools` |
| 加模型提供方 | `ctx.llm` |
| 加 shell 命令执行 | `ctx.shell` |
| 加持久终端 | `ctx.terminals` |
| 加后台工作 | `ctx.jobs` |
| 加用户命令（无需模型） | `ctx.commands` |
| 加文件系统访问 | `ctx.fs` |

## 进阶

- **嵌套 schema**：`parameters` 可以嵌套对象 / 数组 / 联合类型
- **后台任务**：`run_in_background` + `ctx.jobs.start({ kind, label, owner, run })`
- **UI 卡片**：`presentCall` / `presentResult` 自定义卡片样式
- **拦截请求**：`ctx.on('agent/pre-step', ..., 'waterfall')` + 必须调 `next()`
- **官方参考实现**：`packages/shell/tool-bash`（Bash 工具三包套）

📖 详见 `docs/cookbook/adding-a-tool.zh.md` 和 `docs/user/develop/basic/tool.md`