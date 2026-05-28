from seekflow.chat.chat_engine import build_chat_messages


def test_build_chat_messages_preserves_turn_order(conversation_history) -> None:
    messages = build_chat_messages(conversation_history, "Explain Python descriptors")
    assert messages[-1]["role"] == "user"
    assert messages[-1]["content"] == "Explain Python descriptors"
