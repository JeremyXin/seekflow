from pathlib import Path

from seekflow.config import save_config
from seekflow.knowledge.reader import delete_entry, list_entries, read_entry, search_entries
from seekflow.knowledge.writer import build_chat_kb_entry, save_entry


def parse_command(text: str) -> tuple[str, list[str]]:
    parts = text.lstrip("/").split()
    return parts[0], parts[1:]


async def handle_command(text: str, config, emit, latest_chat=None) -> None:
    command, args = parse_command(text)

    if command == "help":
        await emit(
            "/help /provider list /provider switch <name> /provider status /kb list /kb search <query> "
            "/kb show <path> /kb delete <path> /config show /save /exit"
        )
        return

    if command == "config" and args == ["show"]:
        await emit(f"default_provider={config.app.default_provider}")
        await emit(f"kb_dir={config.knowledge_base.kb_dir}")
        return

    if command == "provider" and args[:1] == ["list"]:
        names = ", ".join(config.providers.keys())
        await emit(f"Providers: {names}")
        return

    if command == "provider" and args[:1] == ["status"]:
        await emit(f"Current provider: {config.app.default_provider}")
        return

    if command == "provider" and args[:1] == ["switch"] and len(args) == 2:
        name = args[1]
        if name not in config.providers:
            await emit(f"Unknown provider: {name}")
            return
        config.app.default_provider = name
        save_config(config)
        await emit(f"Switched provider to {name}")
        return

    if command == "kb" and args[:1] == ["list"]:
        entries = list_entries(config.knowledge_base.kb_dir)
        await emit("\n".join(str(item.get("title", item["file_path"])) for item in entries) or "No KB entries found")
        return

    if command == "kb" and args[:1] == ["search"] and len(args) >= 2:
        query = " ".join(args[1:])
        entries = search_entries(config.knowledge_base.kb_dir, query)
        await emit("\n".join(str(item.get("title", item["file_path"])) for item in entries) or "No matches found")
        return

    if command == "kb" and args[:1] == ["show"] and len(args) == 2:
        await emit(read_entry(Path(args[1])))
        return

    if command == "kb" and args[:1] == ["delete"] and len(args) == 2:
        deleted = delete_entry(Path(args[1]))
        await emit("Deleted" if deleted else "Not found")
        return

    if command == "save":
        if latest_chat is None:
            await emit("No chat exchange available to save.")
            return
        user_text, assistant_text = latest_chat
        entry = build_chat_kb_entry(user_text, assistant_text, config)
        path = await save_entry(
            entry,
            config.knowledge_base.kb_dir,
            obsidian_mode=config.knowledge_base.obsidian_mode,
        )
        await emit(f"Saved chat to {path}")
        return

    await emit(f"Unknown command: {text}")
