from app.core.ollama_client import generate_chat, generate_embedding
from app.services.services_vector_db import search_similar_chunks
from app.services.prompt_builder import build_rag_prompt
import asyncio

async def execute_llm_generation(prompt: str, raw_chunks: list[dict]):
      raw_answer = await generate_chat(prompt)

      if ("Tôi không tìm thấy thông tin này" in raw_answer):
            return {"answer": raw_answer, "sources": [], "no_answer_reason": "out_of_scope"}
      else:
            return {"answer": raw_answer, "sources": raw_chunks, "no_answer_reason": None}

async def process_rag_pipeline(question: str):
      embedded_text = await generate_embedding(question)
      document = search_similar_chunks(embedded_text, top_k = 5)     
      prompt = build_rag_prompt(question, document)

      return await execute_llm_generation(prompt, document)