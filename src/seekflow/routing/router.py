import json
import re

from openai import AsyncOpenAI

from seekflow.models import AppConfig, RouteDecision


ROUTER_SYSTEM_PROMPT = """Classify non-command input.
Return JSON only: {"mode":"chat"|"search","reason":"..."}.
Use "search" only when external or current web information is needed.
"""


def parse_route_decision(payload: str) -> RouteDecision:
    text = payload.strip()
    fenced_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced_match:
        text = fenced_match.group(1)
    elif not text.startswith("{"):
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            text = text[start : end + 1]

    data = json.loads(text)
    decision = RouteDecision(mode=data["mode"], reason=data["reason"])
    if decision.mode not in {"chat", "search"}:
        raise ValueError(f"Unsupported route mode: {decision.mode}")
    return decision


async def _complete_route_prompt(text: str, config: AppConfig) -> str:
    client = AsyncOpenAI(api_key=config.llm.api_key, base_url=config.llm.base_url)
    response = await client.chat.completions.create(
        model=config.llm.model,
        messages=[
            {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
    )
    return response.choices[0].message.content or '{"mode":"chat","reason":"empty response"}'


async def route_user_input(text: str, config: AppConfig) -> RouteDecision:
    payload = await _complete_route_prompt(text, config)
    try:
        return parse_route_decision(payload)
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return RouteDecision(
            mode="search",
            reason="Router output was invalid; falling back to web search.",
        )
