from app.core.ollama_client import generate_chat

async def execute_llm_generation(prompt: str, raw_chunks: list[dict]):
      raw_answer = await generate_chat(prompt)

      if ("Tôi không tìm thấy thông tin này" in raw_answer):
            return {"answer": raw_answer, "sources": [], "no_answer_reason": "out_of_scope"}
      else:
            return {"answer": raw_answer, "sources": raw_chunks, "no_answer_reason": None}
      