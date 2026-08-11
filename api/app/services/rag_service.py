import os
import re
from sqlite3 import OperationalError

from app.core.exceptions import (
    RAG_ChromaError,
    RAG_InvalidDimensionException,
    RAG_OperationalError,
    RAG_VectorDBError,
)
from app.core.ollama_client import generate_chat, generate_embedding
from app.services.prompt_builder import build_rag_prompt
from app.services.services_vector_db import search_similar_chunks
from chromadb.errors import ChromaError, InvalidDimensionException

RAG_HISTORY_LIMIT = int(os.getenv("RAG_HISTORY_LIMIT", "6"))

async def execute_llm_generation(prompt: str, raw_chunks: list[dict]) -> dict:
      raw_answer = await generate_chat(prompt)
          
      if "Tôi không tìm thấy" in raw_answer or "không có thông tin" in raw_answer:
            return {
                  "answer": "Tôi không tìm thấy thông tin này trong tài liệu.",
                  "sources": [],
                  "no_answer_reason": "insufficient_context"
            }

      total_chunks = len(raw_chunks)
      valid_chunk_labels = [i for i in range(1, total_chunks + 1)]

      found_labels = re.findall(r"\[S(\d+)\]", raw_answer)

      # Lọc các nhãn thừa
      answer_labels = list(
          dict.fromkeys(int(label) for label in found_labels)
      )

      valid_sources = []

      for label in answer_labels:
            if label not in valid_chunk_labels:
                  citation_str = f"[S{label}]"
                  raw_answer = raw_answer.replace(f"{citation_str} ", "").replace(citation_str, "")
            else:
                  valid_sources.append(raw_chunks[label - 1])

      if not valid_sources:
            return {
                  "answer": "Tôi không tìm thấy thông tin này trong tài liệu.",
                  "sources": [],
                  "no_answer_reason": "insufficient_context",
            }

      return {
            "answer": raw_answer,
            "sources": valid_sources,
            "no_answer_reason": None,
      }


async def process_rag_pipeline(
      question: str, chat_history: list[dict] | None = None
 ) -> dict:
      embedded_text = await generate_embedding(question)

      try:
            document = search_similar_chunks(embedded_text, top_k = 5)
      except InvalidDimensionException:
            raise RAG_InvalidDimensionException("Lỗi hong phù hợp kích thước")
      except OperationalError:
            raise RAG_OperationalError("Lỗi SQLite")
      except ChromaError:
            raise RAG_ChromaError("Lỗi ChromaDB")
      except Exception:
            raise RAG_VectorDBError("Lỗi VectorDB")

      if not document:
            return {
                  "answer": "Tôi không tìm thấy thông tin này trong tài liệu.",
                  "sources": [],
                  "no_answer_reason": "insufficient_context",
            }

      recent_history = []

      for message in (chat_history or [])[-RAG_HISTORY_LIMIT:]:
            if hasattr(message, "model_dump"):
                  message = message.model_dump()

            if not isinstance(message, dict):
                  continue

            role = message.get("role")
            content = message.get("content")

            if role not in {"user", "assistant"}:
                  continue

            if not isinstance(content, str) or not content.strip():
                  continue

            recent_history.append({
                  "role": role,
                  "content": content.strip(),
            })

      prompt = build_rag_prompt(
            question,
            document,
            recent_history,
      )

      return await execute_llm_generation(
            prompt,
            document,
      )
