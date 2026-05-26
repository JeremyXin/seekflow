import httpx
import trafilatura
from bs4 import BeautifulSoup
from readability import Document


def truncate_for_context(text: str, max_words: int = 1500) -> str:
    words = text.split()
    return " ".join(words[:max_words])


async def extract_content(url: str, timeout: int = 15) -> str:
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(url, headers={"User-Agent": "SeekFlow/0.1.0"})
            response.raise_for_status()
    except httpx.HTTPError:
        return ""

    html = response.text
    extracted = trafilatura.extract(html) or ""
    if not extracted.strip():
        extracted = BeautifulSoup(Document(html).summary(), "html.parser").get_text(" ", strip=True)
    if not extracted.strip():
        extracted = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
    return truncate_for_context(extracted)
