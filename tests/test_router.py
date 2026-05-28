import pytest

from seekflow.models import ConversationTurn, RouteDecision


def test_route_decision_defaults_to_reason_text() -> None:
    decision = RouteDecision(mode="chat", reason="general question")
    assert decision.mode == "chat"
    assert decision.reason == "general question"


def test_conversation_turn_stores_role_and_content() -> None:
    turn = ConversationTurn(role="user", content="What is Python GIL?")
    assert turn.role == "user"
    assert turn.content == "What is Python GIL?"


def test_parse_route_decision_reads_json_payload() -> None:
    from seekflow.routing.router import parse_route_decision

    decision = parse_route_decision('{"mode":"search","reason":"needs current web info"}')
    assert decision == RouteDecision(mode="search", reason="needs current web info")


def test_parse_route_decision_reads_fenced_json_payload() -> None:
    from seekflow.routing.router import parse_route_decision

    decision = parse_route_decision('```json\n{"mode":"chat","reason":"general request"}\n```')
    assert decision == RouteDecision(mode="chat", reason="general request")


@pytest.mark.asyncio
async def test_route_user_input_returns_chat_by_default(mocker, app_config) -> None:
    mock_response = mocker.patch("seekflow.routing.router._complete_route_prompt")
    mock_response.return_value = '{"mode":"chat","reason":"general reasoning request"}'

    from seekflow.routing.router import route_user_input

    decision = await route_user_input("Explain decorators", app_config)
    assert decision.mode == "chat"


@pytest.mark.asyncio
async def test_route_user_input_falls_back_to_search_on_invalid_payload(mocker, app_config) -> None:
    mock_response = mocker.patch("seekflow.routing.router._complete_route_prompt")
    mock_response.return_value = "search please"

    from seekflow.routing.router import route_user_input

    decision = await route_user_input("latest Python release", app_config)
    assert decision == RouteDecision(
        mode="search",
        reason="Router output was invalid; falling back to web search.",
    )
