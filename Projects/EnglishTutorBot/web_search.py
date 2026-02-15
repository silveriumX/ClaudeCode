"""
Web Search Integration for EnglishTutorBot
==========================================
DuckDuckGo search with smart query detection.
"""

import re
import logging
from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def search_web(query: str, max_results: int = 3) -> List[Dict[str, str]]:
    """
    Search DuckDuckGo and return results.

    Args:
        query: Search query string
        max_results: Maximum number of results to return

    Returns:
        List of dicts with keys: title, snippet, url
    """
    # Validate query
    if not query or len(query) < 3 or len(query) > 200:
        logger.warning(f"Invalid search query length: {len(query) if query else 0}")
        return []

    # Sanitize special characters
    query = re.sub(r'[^\w\s\-?.,]', '', query)

    url = "https://html.duckduckgo.com/html/"
    params = {"q": query}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    try:
        response = requests.post(url, data=params, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        results = []

        for result in soup.find_all('div', class_='result')[:max_results]:
            title_elem = result.find('a', class_='result__a')
            snippet_elem = result.find('a', class_='result__snippet')

            if title_elem:
                title = title_elem.get_text(strip=True)
                url_link = title_elem.get('href', '')
                snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

                results.append({
                    "title": title,
                    "snippet": snippet[:200],  # Limit snippet length
                    "url": url_link
                })

        logger.info(f"Search '{query}' returned {len(results)} results")
        return results

    except requests.exceptions.Timeout:
        logger.error(f"Search timeout for: {query}")
        return []
    except Exception as e:
        logger.error(f"Search error for '{query}': {e}")
        return []


def format_search_results(results: List[Dict[str, str]]) -> str:
    """
    Format search results for LLM context.

    Args:
        results: List of search result dicts

    Returns:
        Formatted string for GPT context
    """
    if not results:
        return ""

    formatted = "\n\n--- WEB SEARCH RESULTS ---\nSearch results:\n\n"

    for i, result in enumerate(results, 1):
        formatted += f"{i}. {result['title']}\n"
        formatted += f"   {result['snippet']}\n"
        formatted += f"   Source: {result['url']}\n\n"

    return formatted


def should_search(user_message: str, conversation_history: List[Dict] = None) -> Optional[str]:
    """
    Determine if web search is needed based on user message.

    Args:
        user_message: User's message text
        conversation_history: Recent conversation (unused for now)

    Returns:
        Search query if search needed, None otherwise
    """
    # Validate input
    if not user_message or len(user_message) > 500:
        return None

    # Sanitize message
    sanitized_query = user_message.strip()

    # Keywords that trigger search
    search_keywords = [
        # English
        "latest", "recent", "current", "today", "this week", "this month",
        "news", "what's happening", "what happened", "update", "now",
        "who won", "when is", "where is", "how much",

        # Russian
        "последние", "недавние", "текущие", "сегодня", "на этой неделе",
        "новости", "что произошло", "обновление", "сейчас",
        "кто выиграл", "когда", "где", "сколько стоит"
    ]

    # Check if message contains search keywords
    message_lower = user_message.lower()
    for keyword in search_keywords:
        if keyword in message_lower:
            # Extract query (use full message for now)
            final_query = sanitized_query
            logger.debug(f"Search triggered by keyword '{keyword}': {final_query[:50]}")
            return final_query

    return None


if __name__ == "__main__":
    # Quick test
    logging.basicConfig(level=logging.INFO)

    # Test search
    results = search_web("latest AI news 2026", max_results=3)
    print(f"\nFound {len(results)} results:")
    for r in results:
        print(f"- {r['title']}")
        print(f"  {r['url']}\n")

    # Test detection
    test_messages = [
        "What's the latest news about AI?",
        "I like programming",
        "Tell me about the weather today"
    ]

    for msg in test_messages:
        query = should_search(msg)
        print(f"'{msg}' -> {'Search: ' + query if query else 'No search'}")
