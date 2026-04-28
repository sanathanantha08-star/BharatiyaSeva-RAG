from __future__ import annotations
import logging
from langchain_cohere import ChatCohere
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.core.config import settings

logger = logging.getLogger(__name__)

_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are a helpful assistant that answers questions about Indian government welfare schemes.
Use ONLY the context provided below to answer. If the answer is not in the context, say "I don't have enough information."

Context:
{context}""",
    ),
    ("human", "{query}"),
])


class LLMService:

    def __init__(self):
        self._llm = ChatCohere(
            cohere_api_key=settings.llm_api_key,
            model=settings.llm_model_name,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
        )
        self._chain = _PROMPT | self._llm | StrOutputParser()

    async def generate(self, query: str, context_chunks) -> str:
        context = "\n\n---\n\n".join(
            c.parent_text if c.parent_text else c.text
            for c in context_chunks
        )
        logger.debug("Generating answer for query: %s", query)
        return await self._chain.ainvoke({"query": query, "context": context})