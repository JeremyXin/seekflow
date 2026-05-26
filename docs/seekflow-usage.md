# SeekFlow CLI 使用说明

## 1. 简介

SeekFlow 是一个命令行搜索工具。你可以在终端中输入问题，调用搜索源抓取结果，用 LLM 生成带引用的回答，并把结果保存为本地 Markdown 知识条目。

当前版本适合：

- 技术搜索
- 快速研究
- 终端内知识沉淀

## 2. 安装

在项目根目录执行：

```bash
pip install -e .
```

如果你希望使用 Playwright provider，还需要安装浏览器依赖：

```bash
pip install -e .[browser]
playwright install chromium
```

## 3. 初始化配置

首次使用执行：

```bash
seekflow init
```

默认会生成配置文件：

```text
~/.seekflow/config.toml
```

如果你不想写到默认 home 目录，可以临时指定：

```bash
SEEKFLOW_CONFIG_PATH=/your/path/config.toml seekflow init
```

## 4. 配置 LLM

SeekFlow 的完整搜索回答流程依赖 LLM API Key。当前最简单的配置方式是环境变量：

```bash
export SEEKFLOW_LLM_API_KEY="your-api-key"
export SEEKFLOW_LLM_BASE_URL="https://api.openai.com/v1"
export SEEKFLOW_LLM_MODEL="gpt-4o-mini"
```

也可以直接编辑 `config.toml` 中的 `[llm]` 段。

如果没有配置 `SEEKFLOW_LLM_API_KEY`，SeekFlow 可以启动，但无法执行真实搜索回答流程。

## 5. 默认配置结构

当前配置文件大致如下：

```toml
[llm]
api_key = ""
base_url = "https://api.openai.com/v1"
model = "gpt-4o-mini"

[app]
default_provider = "duckduckgo"
max_results = 5
extract_top_n = 3

[knowledge_base]
kb_dir = "~/.seekflow/knowledge"
obsidian_mode = false
obsidian_vault_path = ""
obsidian_subfolder = "SeekFlow"

[providers.duckduckgo]
enabled = true

[providers.brave]
enabled = false
api_key = ""

[providers.serpapi]
enabled = false
api_key = ""

[providers.playwright]
enabled = false
browser = "chromium"
headless = false
```

## 6. 启动方式

执行：

```bash
seekflow
```

正常情况下会进入 REPL：

```text
seekflow>
```

如果只是查看版本：

```bash
seekflow --version
```

## 7. 基本搜索流程

进入 REPL 后，直接输入自然语言问题即可：

```text
seekflow> What is Python GIL?
```

执行过程大致是：

1. 先显示搜索来源
2. 再流式输出回答
3. 最后提示保存路径

如果成功，结果会被保存到本地知识库目录。

## 8. Slash Commands

当前支持以下命令。

### 8.1 帮助

```text
/help
```

显示支持的命令列表。

### 8.2 退出

```text
/exit
/quit
```

退出 REPL。

### 8.3 查看 provider

```text
/provider list
```

列出当前支持的 provider 名称。

### 8.4 查看当前 provider

```text
/provider status
```

查看当前默认 provider。

### 8.5 切换 provider

```text
/provider switch duckduckgo
/provider switch brave
/provider switch serpapi
/provider switch playwright
```

这个命令会修改当前配置并持久化到配置文件。

注意：

- `brave` 需要 API Key
- `serpapi` 需要 API Key
- `playwright` 需要安装浏览器依赖

### 8.6 查看配置

```text
/config show
```

当前会显示基础运行配置，例如默认 provider 和知识库路径。

### 8.7 查看知识库列表

```text
/kb list
```

列出当前知识库中的 Markdown 条目。

### 8.8 搜索知识库

```text
/kb search python
```

在已保存的 Markdown 内容中做简单文本匹配。

### 8.9 查看单条知识条目

```text
/kb show /absolute/path/to/file.md
```

输出指定 Markdown 文件的内容。

### 8.10 删除知识条目

```text
/kb delete /absolute/path/to/file.md
```

删除指定 Markdown 文件。

## 9. 当前 provider 说明

### 9.1 DuckDuckGo

默认 provider，零配置可用。

适合：

- 快速开始
- 无 API Key 的开发环境

### 9.2 Brave

需要配置 Brave Search API Key。

### 9.3 SerpAPI

需要配置 SerpAPI Key。

### 9.4 Playwright

通过浏览器方式执行搜索，适合某些普通 HTTP 搜索不稳定的场景。

需要：

```bash
pip install -e .[browser]
playwright install chromium
```

## 10. 知识库存储规则

默认知识库目录是：

```text
~/.seekflow/knowledge
```

落盘路径格式为：

```text
YYYY-MM/category/slug.md
```

例如：

```text
~/.seekflow/knowledge/2026-05/programming/what-is-python-gil.md
```

每个文件包含：

- frontmatter 元数据
- `## Answer`
- `## Sources`

## 11. Obsidian 模式

如果你希望把 SeekFlow 的输出直接写成更兼容 Obsidian 的 Markdown，可以在配置中打开：

```toml
[knowledge_base]
obsidian_mode = true
```

这样 frontmatter 会附加更适合 Obsidian 的字段。

如果你希望直接把输出写到 Vault 中，可以进一步设置：

```toml
[knowledge_base]
obsidian_mode = true
obsidian_vault_path = "/path/to/your/vault"
obsidian_subfolder = "SeekFlow"
```

## 12. 常见问题

### 12.1 为什么启动后提示 LLM API key 未配置？

因为当前版本要求在执行真实搜索回答前，必须先提供 `SEEKFLOW_LLM_API_KEY` 或在配置文件中填写 `llm.api_key`。

### 12.2 为什么切到 Brave 或 SerpAPI 后不能用？

因为这两个 provider 都依赖各自的 API Key。只切换 provider 名称并不会自动补全凭据。

### 12.3 为什么 Playwright provider 不可用？

通常是以下原因之一：

- 没安装 `playwright` Python 包
- 没执行 `playwright install chromium`
- 本地环境无法正常启动浏览器

### 12.4 为什么 `/kb show` 和 `/kb delete` 要求路径？

当前版本的 KB 命令是 MVP 实现，没有做交互式选择器或短 ID 映射，所以直接使用文件路径。

## 13. 推荐使用流程

推荐按下面顺序使用：

1. `seekflow init`
2. 配置 `SEEKFLOW_LLM_API_KEY`
3. 执行 `seekflow`
4. 用默认 `duckduckgo` 做第一条搜索
5. 用 `/kb list` 确认条目已落盘
6. 按需切换到 `brave`、`serpapi` 或 `playwright`

## 14. 当前版本限制

当前版本仍然是 MVP，已知限制包括：

- 不支持 `/config set`
- KB 搜索是简单文本匹配，不是语义检索
- 没有自动 provider failover
- 没有多 provider 聚合搜索
- 没有完整的富文本交互浏览

但对于“终端里提问并把结果保存成 Markdown”这一目标，当前版本已经具备完整基本能力。
