# 费曼学AI · 造物车间

> 每期一个可带走的工作。不教「看懂」，教「造出来」。

这是 [费曼学AI](https://space.bilibili.com/3706955411490829) 频道「造物车间」系列的公开资产仓库。每一期视频对应一份可直接接入项目的代码、模板或检查清单——改几个配置就能跑，不是示例代码。

---

## 已发布

| # | 主题 | 资产数 | 视频 | 发布日期 |
|---|------|:---:|------|:---:|
| 01 | [Agent 记忆系统](./episodes/01-agent-memory-system/) | 4 份 | [B站](https://www.bilibili.com/video/BV1uiEM6xE9s/) | 2026-06-08 |
| 02 | [意图识别：从 if-else 到生产级](./episodes/02-intent-recognition/) | 4 份 | [B站](https://www.bilibili.com/video/BV1xx411c7mD/) | 2026-06-11 |
| 03 | [7层 Pipeline 打通多源文档解析](./episodes/03-doc-parse-pipeline/) | 4 份 | [B站](https://www.bilibili.com/video/BV1xx411c7mD/) | 2026-06-12 |
| 04 | [文件切分与召回：6种切法×3层架构实测](./episodes/04-chunking-retrieval/) | 5 份 | [B站](https://www.bilibili.com/video/BV1iCLR6xExi/) | 2026-06-17 |
| 05 | [Rerank + 置信度校准](./episodes/05-rerank-calibration/) | 2 份 | [B站](https://www.bilibili.com/video/BV1xxx/) | 2026-06-19 |
| 06 | [Agent Loop：50行代码×4控制点×1套Harness](./episodes/06-agent-loop/) | 3 份 | [B站](https://www.bilibili.com/video/BV1xxx/) | 2026-06-30 |

---

## 怎么用这个仓库

每一期目录下的 README 都有「5 分钟快速上手」指南：

1. 进入 `episodes/XX-xxx/` 
2. 读本期 README，搞清楚资产之间的关系
3. 按顺序使用：一般先填工作表 → 再改代码 → 对照决策树 → 跑压测
4. 遇到问题？去对应视频评论区聊

---

## 资产类型说明

| 文件前缀 | 用途 | 例子 |
|:---|:---|:---|
| `worksheet-` | 填空式工作表，先想清楚再动手 | 三分类记忆工作表 |
| `code-` | 可直接接入的代码骨架 | Python 代码骨架 |
| `decision-tree-` | 技术选型决策树，逐项对照 | 七步架构决策树 |
| `testcases-` | 验证检查清单，每加一层跑一次 | 五个压测用例 |

---

## 许可

MIT — 随便用，提到来源就行。详见 [LICENSE](./LICENSE)。

---

## 贡献

欢迎对资产改进提 PR。详见 [CONTRIBUTING.md](./CONTRIBUTING.md)。
