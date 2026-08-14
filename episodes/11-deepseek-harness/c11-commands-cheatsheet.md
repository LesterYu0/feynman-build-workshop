# 5 条核心命令速查表（C11 置顶资产 1/5）

> DeepSeek Harness（dsh）日常使用的 5 条命令，**抄走就能用**。

## 1. 一键启动 Web UI

```sh
npx @deepseek-ai/dsh web
```

默认地址：`http://127.0.0.1:3080`

无需 Node 以外的任何依赖，第一次跑会自动下载。配置模型在「设置 → 模型」里填 API key，路由立即生效，不用重启服务器。

## 2. 源码构建（自定义 / 二次开发用）

```sh
git clone https://github.com/deepseek-ai/deepseek-harness.git
cd deepseek-harness
pnpm install
pnpm run build
pnpm dsh web
```

依赖几百 MB，build 数分钟。日常使用**不需要走这条路**，npx 一行就够。

## 3. 无人值守 / CI 跑任务

```sh
export DEEPSEEK_API_KEY=sk-your-key-here
pnpm dsh --profile headless "修复这个工作区里失败的测试"
```

接受一个任务字符串，创建持久会话，跑完打印最终回答并退出。适合塞进 CI 或批量跑 benchmark。

⚠️ 必须设 `DEEPSEEK_API_KEY`，**否则直接报 `MISSING_CREDENTIAL`**。

## 4. 查看你的真实配置树

```sh
pnpm dsh --profile web --dump-config
```

打印当前 profile 的完整插件树（dsh-base / dsh-web-app / 你的 patch），每一条都能被你的 patch 替换。**第一次装完必跑**，先看引擎长什么样。

## 5. 管理 profile 的插件

```sh
pnpm dsh plugin --profile <profile 名> <pnpm 参数>
```

把剩下的参数透传给 pnpm。常用：

```sh
# 给 web profile 加一个第三方插件
pnpm dsh plugin --profile web add @your-org/your-plugin

# 更新插件
pnpm dsh plugin --profile web update
```

---

## 常用参数

| 参数 | 作用 | 示例 |
|---|---|---|
| `--profile <name>` | 选择 profile | `--profile headless` |
| `--patch <path>` | 加载自定义 patch overlay（可重复） | `--patch ./scratch-plugin/cordis.yml` |
| `--port <n>` | Web UI 端口（透传给 web app） | `--port 9000` |
| `--dump-config` | 打印配置树后退出 | — |
| `--dump-default-config` | 打印无用户层的默认配置树 | — |
| `-V` / `--version` | 版本号 | — |

---

## 反直觉点

- `dsh web` 等价于 `dsh --profile web`，是别名
- 参数分两层：launcher 的（`--profile / --patch / --dump-config`）和 app 的（透传给 profile，如 `--port`），**launcher 参数必须在前**
- `--patch` 可重复叠加：profile patch → home patch → 命令行 overlay（层级错了你的改动就被覆盖）