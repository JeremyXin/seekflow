# SeekFlow CLI 实现原理与架构说明

## 1. 项目定位

SeekFlow 是一个基于 Python 的命令行搜索助手。它的目标不是做浏览器替代品，而是在终端里把这几件事串成一个稳定流程：

1. 接收自然语言问题
2. 调用搜索源获取候选结果
3. 提取网页正文
4. 交给 LLM 生成带引用的回答
5. 将结果沉淀为本地 Markdown 知识条目

当前实现是一个以 REPL 为中心的 CLI 工具，强调：

- 可本地保存
- 可切换搜索源
- 可复查来源
- 可持续扩展

## 2. 总体架构

SeekFlow 当前采用“路由层 + 执行层 + 持久化层”的实现方式。

```text
User Input
   |
   v
Typer CLI / REPL
   |
   +--> Slash Command Router
   |       |
   |       +--> Provider Commands
   |       +--> KB Commands
   |       +--> Config Show / Save Chat
   |
   +--> LLM Router
           |
           +--> Chat Engine
           |
           +--> Search Pipeline
           |
           +--> Provider Registry -> Active Provider
           +--> Content Extraction
           +--> LLM Synthesis
           +--> Metadata Generation
           +--> Markdown KB Writer
```

核心设计原则：

- CLI 只负责交互，不负责业务决策
- provider 只负责搜索，不负责正文提取
- pipeline 负责编排，不负责终端显示
- knowledge 模块只负责落盘和读取
- synthesis 模块只负责 LLM 上下文构造与生成

## 3. 入口层

入口文件是 [src/seekflow/cli.py](/Users/songjiayin/Leibaoxin/plugin/llm_based_search_engine_cli/src/seekflow/cli.py:1)。

它承担三件事：

- 暴露 `seekflow --version`
- 暴露 `seekflow init`
- 在没有子命令时启动 REPL

启动流程是：

1. 先调用 `ensure_config_exists()`，确保配置文件存在
2. 再调用 `load_config()` 读取运行时配置
3. 通过 `asyncio.run(run_repl(config))` 启动异步 REPL

这意味着 `seekflow` 的默认使用方式就是直接进入交互会话，而不是一次性执行单条命令。

## 4. 配置系统

配置实现位于 [src/seekflow/config.py](/Users/songjiayin/Leibaoxin/plugin/llm_based_search_engine_cli/src/seekflow/config.py:1)。

### 4.1 配置来源

当前支持两层来源：

- 配置文件
- 环境变量覆盖

默认配置路径：

- `~/.seekflow/config.toml`

测试或特殊场景下也支持：

- `SEEKFLOW_CONFIG_PATH`

用于重定向配置文件路径。

### 4.2 配置对象模型

运行时配置会被加载为 `AppConfig`，内部再拆成：

- `LLMConfig`
- `AppRuntimeConfig`
- `KnowledgeBaseConfig`
- `providers`

这样的好处是：

- 配置边界明确
- 后续扩展字段时不会把所有设置堆在同一个对象上
- 模块之间可以只依赖自己需要的那一部分配置

### 4.3 安全策略

`save_config()` 写完配置文件后会执行 `chmod 600`，确保 API Key 不会以过宽权限暴露。

## 5. REPL 与命令路由

REPL 实现在 [src/seekflow/repl/session.py](/Users/songjiayin/Leibaoxin/plugin/llm_based_search_engine_cli/src/seekflow/repl/session.py:1)，命令路由实现在 [src/seekflow/repl/commands.py](/Users/songjiayin/Leibaoxin/plugin/llm_based_search_engine_cli/src/seekflow/repl/commands.py:1)。

### 5.1 输入分发规则

输入处理规则分两层：

- 以 `/` 开头：按 slash command 处理
- 否则：先交给 LLM router 判断是 `chat` 还是 `search`

这样设计的目的是：

- slash command 保持显式语法，不依赖模型猜测
- 普通自然语言输入可以优先按聊天理解
- 只有确实需要外部或最新信息时才触发搜索工具链

### 5.2 当前命令集合

当前实现支持：

- `/help`
- `/provider list`
- `/provider switch <name>`
- `/provider status`
- `/kb list`
- `/kb search <query>`
- `/kb show <path>`
- `/kb delete <path>`
- `/config show`
- `/save`
- `/exit`
- `/quit`

### 5.3 历史记录

REPL 使用 `PromptSession + FileHistory`，命令历史会保存到：

- `~/.seekflow/history`

对应代码在 `build_session()` 中。

## 6. Provider 架构

Provider 体系由以下文件组成：

- [src/seekflow/providers/base.py](/Users/songjiayin/Leibaoxin/plugin/llm_based_search_engine_cli/src/seekflow/providers/base.py:1)
- [src/seekflow/providers/registry.py](/Users/songjiayin/Leibaoxin/plugin/llm_based_search_engine_cli/src/seekflow/providers/registry.py:1)
- `src/seekflow/providers/*.py`

### 6.1 抽象边界

`SearchProvider` 抽象类定义两个最小接口：

- `search(query, num_results)`
- `is_available()`

这保证所有 provider 都满足统一契约，pipeline 不需要知道它背后是：

- DuckDuckGo
- Brave
- SerpAPI
- Playwright

### 6.2 注册机制

`ProviderRegistry` 通过装饰器注册 provider 类。

好处是：

- pipeline 可以按名字获取 provider
- 不需要写复杂的动态插件发现
- MVP 阶段扩展成本足够低

### 6.3 当前 provider 列表

当前已实现：

- `duckduckgo`
- `brave`
- `serpapi`
- `playwright`

其中：

- DuckDuckGo 是默认 provider，零配置可用
- Brave 和 SerpAPI 依赖 API Key
- Playwright 依赖本地浏览器环境

## 7. 路由层

当前输入路由规则是：

- `/` 开头：直接进入 `command`
- 非 `/` 输入：先进入 LLM router
- router 只输出两种结果：
  - `chat`
  - `search`

这样 SeekFlow 的行为更接近 agent 的 tool-call 风格，但仍保留程序端的明确控制。

## 8. Chat 主流程

纯 chat 模式使用当前配置中的同一个模型，不触发 provider 搜索。

执行顺序：

1. 读取当前会话历史
2. 构造 chat prompt
3. 流式输出回答
4. 将本轮 user / assistant 内容保存在内存会话历史中
5. 默认不保存到 KB

如果用户认为这轮 chat 有价值，可以后续使用 `/save` 手动落盘。

## 9. 搜索主流程

主流程实现在 [src/seekflow/pipeline.py](/Users/songjiayin/Leibaoxin/plugin/llm_based_search_engine_cli/src/seekflow/pipeline.py:1)。

`SearchPipeline.run()` 的执行顺序如下：

1. 根据 `config.app.default_provider` 从注册表取 provider
2. 调用 `provider.is_available()` 做可用性检查
3. 调用 `provider.search()` 获取搜索结果
4. 如果没有结果，抛出 `NoResultsError`
5. 通过 `on_sources()` 回调把来源显示给 REPL
6. 对 Top N 结果调用 `extract_content()`
7. 调用 `synthesize_answer()` 流式生成回答
8. 调用 `generate_metadata()` 补充 `summary/tags/category`
9. 组装 `KBEntry`
10. 调用 `save_entry()` 落盘
11. 返回完整 `KBEntry`

### 9.1 为什么用 pipeline

这样做的主要原因不是“结构好看”，而是为了降低耦合：

- CLI 不需要知道搜索和落盘细节
- provider 不需要知道 LLM
- LLM 不需要知道文件系统
- KB 模块不需要知道来源是谁

## 10. 网页正文提取

正文提取位于 [src/seekflow/extraction/extractor.py](/Users/songjiayin/Leibaoxin/plugin/llm_based_search_engine_cli/src/seekflow/extraction/extractor.py:1)。

当前采用降级链：

1. `trafilatura`
2. `readability-lxml`
3. `BeautifulSoup`

原因是搜索结果页通常只包含摘要，而 LLM 回答质量更依赖正文内容。

提取失败时返回空字符串，而不是直接终止整个流程。这样设计是为了让：

- 有正文时优先用正文
- 正文提取失败时仍可以退回 snippet

## 11. LLM 合成层

LLM 相关逻辑位于：

- [src/seekflow/synthesis/prompts.py](/Users/songjiayin/Leibaoxin/plugin/llm_based_search_engine_cli/src/seekflow/synthesis/prompts.py:1)
- [src/seekflow/synthesis/synthesizer.py](/Users/songjiayin/Leibaoxin/plugin/llm_based_search_engine_cli/src/seekflow/synthesis/synthesizer.py:1)

### 9.1 回答生成

`synthesize_answer()` 会：

- 构造引用上下文
- 使用 OpenAI-compatible `chat.completions`
- 开启流式输出
- 将 token chunk 逐段返回给 REPL

### 9.2 元数据生成

`generate_metadata()` 用第二次 LLM 请求生成：

- `summary`
- `tags`

而 `category` 不是自由生成，而是由 `classify_category()` 使用规则法归类。

这样做是为了避免：

- 分类字段随模型风格漂移
- 同类问题被写入多个不同目录

## 12. 知识库落盘

知识库写入实现在 [src/seekflow/knowledge/writer.py](/Users/songjiayin/Leibaoxin/plugin/llm_based_search_engine_cli/src/seekflow/knowledge/writer.py:1)。

### 10.1 路径规则

落盘路径格式：

- `kb_dir / YYYY-MM / category / slug.md`

例如：

- `~/.seekflow/knowledge/2026-05/programming/what-is-python-gil.md`

### 10.2 文件内容

每条知识记录是一个 Markdown 文件，包含：

- YAML frontmatter
- `## Answer`
- `## Sources`

frontmatter 当前包含：

- `title`
- `date`
- `query`
- `summary`
- `tags`
- `category`
- `provider`
- `model`
- `source_urls`

### 10.3 Obsidian 兼容

当 `obsidian_mode=true` 时，会额外写入：

- `aliases`
- `cssclasses`

用于兼容 Obsidian 的属性系统。

## 13. 错误处理策略

当前主要错误类型定义在 [src/seekflow/errors.py](/Users/songjiayin/Leibaoxin/plugin/llm_based_search_engine_cli/src/seekflow/errors.py:1)。

包括：

- `ProviderNotConfiguredError`
- `NoResultsError`
- `LLMError`

CLI 层会捕获异常并通过 formatter 进行错误展示，而不是直接把 traceback 暴露给终端用户。

## 14. 输出层

终端展示位于 [src/seekflow/output/formatter.py](/Users/songjiayin/Leibaoxin/plugin/llm_based_search_engine_cli/src/seekflow/output/formatter.py:1)。

当前输出层负责：

- 错误展示
- 来源展示
- 保存路径提示

这里刻意不放业务逻辑，只做终端显示。

## 15. 测试策略

测试目录在 `tests/`。

当前覆盖了这些层面：

- CLI smoke tests
- config/model tests
- provider registry 与 provider 可用性
- extraction 与 markdown 渲染
- synthesis 辅助逻辑
- pipeline 编排
- REPL 命令解析与路由

整体策略是“小模块可独测，主流程可拼装”。

## 16. 当前实现边界

当前第一版已经可用，但仍然是 MVP：

- 没有 `/config set`
- 没有自动 provider failover
- 没有向量检索或语义搜索
- 没有 PDF/视频/社交媒体提取
- 没有多 provider 聚合
- 没有完整的 TUI/可视化知识库浏览

这意味着当前版本的重点是先把“搜索 -> 回答 -> 保存”主链路跑通，而不是做复杂的平台化能力。

## 17. 后续可扩展方向

比较自然的下一步包括：

- 增加 `/config set`
- provider 状态检查更细化
- 更完整的 Rich 流式展示
- KB 搜索结果的更好格式化
- 真实的 Playwright 端到端集成
- 增加 request 重试、超时和限流处理
- 引入语义索引或全文索引

当前架构已经为这些能力预留了边界，不需要推翻现有设计。
