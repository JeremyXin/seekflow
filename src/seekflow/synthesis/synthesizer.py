import json
from collections.abc import AsyncGenerator

from openai import APIConnectionError, AsyncOpenAI, AuthenticationError, RateLimitError

from seekflow.errors import LLMError
from seekflow.models import AppConfig, SearchResult
from seekflow.synthesis.prompts import ANSWER_SYSTEM_PROMPT, METADATA_SYSTEM_PROMPT


def classify_category(query: str) -> str:
    lowered = query.lower()
    if any(word in lowered for word in ("docker", "kubernetes", "terraform", "ci/cd")):
        return "devops"
    if any(word in lowered for word in ("python", "javascript", "java", "rust", "go", "gil", "api")):
        return "programming"
    if any(word in lowered for word in ("llm", "embedding", "rag", "agent", "transformer")):
        return "ai"
    if any(word in lowered for word in ("research", "paper", "study")):
        return "research"
    if any(word in lowered for word in ("notes", "workflow", "obsidian", "productivity")):
        return "productivity"
    return "general"


def build_context(query: str, results: list[SearchResult], max_words: int = 7500) -> str:
    chunks: list[str] = [f"Query: {query}"]
    for index, result in enumerate(results, start=1):
        body = result.content or result.snippet
        chunks.append(f"[{index}] {result.title}\n{result.url}\n{body}")
    words = "\n".join(chunks).split()
    return " ".join(words[:max_words])


async def synthesize_answer(
    query: str,
    results: list[SearchResult],
    config: AppConfig,
) -> AsyncGenerator[str, None]:
    client = AsyncOpenAI(api_key=config.llm.api_key, base_url=config.llm.base_url)
    try:
        stream = await client.chat.completions.create(
            model=config.llm.model,
            stream=True,
            messages=[
                {"role": "system", "content": ANSWER_SYSTEM_PROMPT},
                {"role": "user", "content": build_context(query, results)},
            ],
        )
    except (AuthenticationError, APIConnectionError, RateLimitError) as exc:
        raise LLMError(str(exc)) from exc
    async for chunk in stream:
        delta = chunk.choices[0].delta.content or ""
        if delta:
            yield delta


async def generate_metadata(query: str, answer: str, config: AppConfig) -> dict[str, object]:
    client = AsyncOpenAI(api_key=config.llm.api_key, base_url=config.llm.base_url)
    response = await client.chat.completions.create(
        model=config.llm.model,
        messages=[
            {"role": "system", "content": METADATA_SYSTEM_PROMPT},
            {"role": "user", "content": f"Query: {query}\nAnswer: {answer}"},
        ],
    )
    payload = json.loads(response.choices[0].message.content)
    return {"summary": payload["summary"], "tags": payload["tags"], "category": classify_category(query)}
