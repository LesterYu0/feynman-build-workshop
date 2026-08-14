# 4 个真实坑排错清单（C11 置顶资产 4/5）

> 我实测跑通 dsh 时踩过的 4 个坑，**官方文档没写全**。按顺序检查基本能解决 90% 的"跑不起来"问题。

## 坑 1：Node 版本过低直接装不上

**症状**：
- `npx @deepseek-ai/dsh web` 报 `EBADENGINE` 或奇奇怪怪的 TypeScript 错误
- `pnpm install` 报 `engines` 不满足

**原因**：`package.json` 硬要求 `node ^22.19.0 || >=24.0.0`。

**修复**：
```sh
node --version  # 必须 ≥ 22.19
# 用 nvm 切换：
nvm install 22.19.0
nvm use 22.19.0
```

---

## 坑 2：源码跑必须先 build

**症状**：
- `git clone` 后直接 `pnpm dsh web` 报 "Cannot find module" 或路径错误
- 报错信息指向一堆 `dist/` 路径

**原因**：dsh 的 lib 是 `tsdown` 打包到 `lib/`，web 前端是 `vite build` 到 `dist/`。**没 build 就没有产物**。

**修复**：
```sh
pnpm install
pnpm run build    # = build:lib + build:web
pnpm dsh web
```

**捷径**：日常用根本不需要源码构建。`npx @deepseek-ai/dsh web` 一行就够。

---

## 坑 3：Web UI 不选工作区，会话输入框不可用

**症状**：
- 启动 `dsh web` 打开 `http://127.0.0.1:3080`
- 会话输入框是灰色禁用状态，点了没反应
- 以为是 bug，重启了好几次

**原因**：官方文档原话："新的 Web UI 在添加工作区前不会选中任何工作区"。

**修复**：
1. 点「选择工作区」
2. 添加你启动 `dsh` 时所在的目录
3. 选中它 → 输入框激活

---

## 坑 4：headless 模式没 API key 直接报错

**症状**：
```sh
$ pnpm dsh --profile headless "hello"
dsh: MISSING_CREDENTIAL: llm-deepseek: no API key for provider route "deepseek-official"
[ELIFECYCLE] Command failed with exit code 1.
```

**原因**：headless 没有 UI 引导填 key，必须环境变量。

**修复**：
```sh
export DEEPSEEK_API_KEY=sk-your-key-here
pnpm dsh --profile headless "你的任务"
```

或者用 Web UI 填好 key（写到凭证服务），headless 会自动读。

---

## 隐藏坑 5：--patch 层级错了配置被覆盖

**症状**：你写了 patch 但不生效。

**原因**：配置树有 4 层叠加顺序：
1. profile 的 `bundles` 列表（按顺序）
2. profile 的 `cordis.patch.yml`
3. home 级 patch（`$DSH_HOME/cordis.patch.yml`）
4. 命令行 `--patch` overlay

**修复**：
- 想给单一 profile 改：写到 `$DSH_HOME/profiles/<name>/cordis.patch.yml`
- 想给本机所有 profile 改：写到 `$DSH_HOME/cordis.patch.yml`
- 想临时测一个 patch：命令行 `--patch <path>`
- **永远用 `insert` 追加新条目，不要直接覆盖文件**（可能包含无关的用户 patch）

---

## 出现奇问题时的 3 个万能排查

```sh
# 1. 看你的实际配置树（patch 叠加后）
pnpm dsh --profile web --dump-config | less

# 2. 看 profile 模板默认配置（不含你的 patch）
pnpm dsh --profile web --dump-default-config | less

# 3. 检查 Node + pnpm 版本
node --version && pnpm --version
```

---

## 还有什么没覆盖的坑？

评论区告诉我你的报错信息，下一期选 3 个复盘。