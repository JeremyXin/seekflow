# SeekFlow Claude-Style TUI Mockup

## Goal

This mockup shows the proposed visual structure for a Claude Code-inspired SeekFlow terminal UI before implementation changes.

## Home State

```text
╭─── SeekFlow v0.1.0 ───────────────────────────────────────────────────────────────────────────────────────────────╮
│                                                    │ Tips for getting started                                      │
│                    Welcome back!                   │ Run /help to inspect commands and shortcuts                   │
│                                                    │ ───────────────────────────────────────────────────────────── │
│                    seekflow                        │ Recent activity                                               │
│                                                    │ 1 saved entry · latest: ni-hao                               │
│                                                    │                                                              │
│        deepseek-v4-pro · duckduckgo search         │                                                              │
│           ~/.seekflow/knowledge                    │                                                              │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

  Try "compare asyncio vs threading in Python"

› Ask SeekFlow to research a topic...

  Enter to send · /help for commands
```

## Conversation State

```text
╭─── SeekFlow v0.1.0 ───────────────────────────────────────────────────────────────────────────────────────────────╮
│                                                    │ Tips for getting started                                      │
│                    Welcome back!                   │ Run /help to inspect commands and shortcuts                   │
│                                                    │ ───────────────────────────────────────────────────────────── │
│                    seekflow                        │ Recent activity                                               │
│                                                    │ 1 saved entry · latest: ni-hao                               │
│                                                    │                                                              │
│        deepseek-v4-pro · duckduckgo search         │                                                              │
│           ~/.seekflow/knowledge                    │                                                              │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

› 你好

  Routing to chat

  SeekFlow
  你好，我可以帮你检索资料、整理答案，或者把结果保存到本地知识库。

› Python asyncio 和 threading 的区别

  Routing to web search
  Searching with duckduckgo

  SeekFlow
  `asyncio` 适合高并发 I/O 协作式任务，`threading` 更适合需要并行等待或兼容阻塞接口的场景。

  Sources
  [1] Python docs - asyncio
  [2] Python docs - threading

› Ask a follow-up...

  Enter to send · /help for commands
```

## Streaming State

```text
╭─── SeekFlow v0.1.0 ───────────────────────────────────────────────────────────────────────────────────────────────╮
│                                                    │ Tips for getting started                                      │
│                    Welcome back!                   │ Run /help to inspect commands and shortcuts                   │
│                                                    │ ───────────────────────────────────────────────────────────── │
│                    seekflow                        │ Recent activity                                               │
│                                                    │ 1 saved entry · latest: ni-hao                               │
│                                                    │                                                              │
│        deepseek-v4-pro · duckduckgo search         │                                                              │
│           ~/.seekflow/knowledge                    │                                                              │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

› 最新的 Python 3.13 有哪些变化

  Routing to web search
  Searching with duckduckgo

  Brewing…
  Tip: /save stores the latest assistant reply in your local knowledge base.

  SeekFlow
  Python 3.13 在解释器性能、错误提示和标准库上都有更新，其中比较值得关注的是...

› Ask a follow-up...

  Enter to send · /help for commands
```

## Notes

- The welcome card is a single, low-height panel.
- The conversation area is not boxed separately.
- Messages are rendered as a lightweight transcript, not heavy bordered cards.
- The composer is minimal and stays visually close to Claude Code.
