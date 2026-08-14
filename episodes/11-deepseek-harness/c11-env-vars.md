# 7 个环境变量清单（C11 置顶资产 3/5）

> DeepSeek Harness（dsh）的核心环境变量速查。**headless 没 API key 直接报错**，这个坑几乎人人踩过。

## 必备

| 变量 | 必填？ | 作用 | 示例 |
|---|:---:|---|---|
| `DEEPSEEK_API_KEY` | ✅ | DeepSeek 兼容 API 凭据 | `DEEPSEEK_API_KEY=sk-your-key-here` |

⚠️ 没设这个跑 headless 会报：
```
dsh: MISSING_CREDENTIAL: llm-deepseek: no API key for provider route "deepseek-official"
```

## 常用

| 变量 | 默认 | 作用 |
|---|---|---|
| `DEEPSEEK_BASE_URL` | DeepSeek 官方 | 改成 OpenAI 兼容代理地址 |
| `DSH_MODEL` | `deepseek-v4-flash` | agent 默认模型 |
| `DSH_CWD` | 启动目录 | agent 的 bash / 文件系统工具的工作区 |
| `DSH_SESSION_ROOT` | `$DSH_HOME/sessions` | 会话 JSONL 日志目录 |
| `DSH_SYSTEM_PROMPT` | 部署提供 | 系统提示词 |
| `DSH_HOME` | `~/.dsh` | Harness home 目录，profile / patch 都放这下面 |

## 进阶

| 变量 | 作用 |
|---|---|
| `DSH_CONTEXT_WINDOW` | `DSH_MODEL` 目录项记录的上下文容量 |
| `DSH_MAX_TOKENS_AS_SUCCESS` | `true`（默认）接受受 token 上限限制的结果 |
| `DSH_CORDIS_CONFIG` | 通过 Python SDK 传入 cordis 配置文件路径 |

## 安全提示

- **stdio MCP 客户端**会主动移除名称像凭据的环境变量和所有 `DSH_*`，其余继承
- **HTTP MCP 客户端**依赖上游服务，必须已运行
- **不要**把 API key 直接写进 YAML 配置，配置项的 `config.env` 里传

## 完整示例

```sh
# 1. DeepSeek 官方 API
export DEEPSEEK_API_KEY=sk-your-key-here

# 2. 换成 OpenAI 兼容代理
export DEEPSEEK_BASE_URL=http://127.0.0.1:8000/v1
export DSH_MODEL=gpt-4o

# 3. 限制 agent 工作区 + 会话目录
export DSH_CWD=/path/to/workspace
export DSH_SESSION_ROOT=/path/to/sessions

# 4. 自定义系统提示词
export DSH_SYSTEM_PROMPT="You are a helpful software engineer assistant."

# 5. 跑 headless 任务
pnpm dsh --profile headless "Inspect the repo and fix failing tests"
```

📖 详见 `docs/user/guide/python-sdk.zh.md` 和 `examples/jsonrpc-agent/README.zh.md`