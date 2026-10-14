"""Ask OptiBot a question against the File Search store.

    python ask.py "How do I add a YouTube video?"
"""

import logging
import sys

from google import genai
from google.genai import types

from kbsync.config import Settings

SYSTEM_PROMPT = """You are OptiBot, the customer-support bot for OptiSigns.com.
• Tone: helpful, factual, concise.
• Only answer using the uploaded docs.
• Max 5 bullet points; else link to the doc.
• Cite up to 3 "Article URL:" lines per reply."""


def main() -> int:
    logging.basicConfig(level=logging.WARNING)
    question = " ".join(sys.argv[1:]) or "How do I add a YouTube video?"
    settings = Settings.from_env()
    client = genai.Client(api_key=settings.api_key)
    store = next(s for s in client.file_search_stores.list() if s.display_name == settings.store_display_name)

    response = client.models.generate_content(
        model=settings.model,
        contents=question,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            tools=[types.Tool(file_search=types.FileSearch(file_search_store_names=[store.name]))],
        ),
    )
    print(f"Q: {question}\n")
    print(response.text)

    grounding = response.candidates[0].grounding_metadata
    titles = {c.retrieved_context.title for c in (grounding.grounding_chunks or []) if c.retrieved_context} if grounding else set()
    if titles:
        print("\nRetrieved from:", ", ".join(sorted(titles)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
