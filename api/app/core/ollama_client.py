import ollama, httpx, asyncio
from ollama import AsyncClient
from app.core.exceptions import AIModelOfflineException, RequestTimeoutError, ModelNotFoundError, InvalidResponseError, EmptyEmbeddingError
                                

client = AsyncClient()

#Cấu hình OLLAMA Client
async def chat():
      try:
            await client.list()
      except (httpx.ConnectError, httpx.TimeoutException):
            raise AIModelOfflineException("Chưa mở Ollama hoặc mất kết nối server")
      except ollama.ResponseError:
            raise AIModelOfflineException("Ollama phản hồi lỗi")
      except Exception:
            raise AIModelOfflineException("Lỗi không xác định khi kết nối Ollama")
      
# Hàm Embedding (Biến chữ thành số)
async def generate_embedding(text: str) -> list[float]:
      try:
            response = await client.embeddings(model = "nomic-embed-text", prompt = text)
      except ollama.ResponseError as e:
            if (e.status_code == 404):
                  raise ModelNotFoundError("Model 'nomic-embed-text' không tồn tại. Vui lòng chạy lệnh: 'ollama pull nomic-embed-text'")
            raise InvalidResponseError("Response không hợp lệ")
      except httpx.ConnectError:
            raise AIModelOfflineException("Ollama ngắt kết nối")
      except httpx.TimeoutException:
            raise RequestTimeoutError("Yêu cầu sinh embedding text hết thời gian chờ")

      if response:
            if (isinstance(response, dict)):
                  content = response.get("embedding")
            else:
                  content = getattr(response, "embedding", None)

            if (not isinstance(content, list) or not content):
                  raise EmptyEmbeddingError("Embedding rỗng")
            
            for embedded_text in content:
                  if (
                        isinstance(embedded_text, bool) or 
                        not isinstance(embedded_text, (int, float))
                  ):
                        raise InvalidResponseError("Response không hợp lệ")
            return content
      else:
            raise InvalidResponseError("Response không hợp lệ")
            
# Hàm Chat (Sinh câu trả lời)
async def generate_chat(prompt: str) -> str:
      message = [{
            'role' : 'user',
            'content' : prompt
      }]
      try:
            response = await client.chat(model = "llama3.2", messages = message, options = {'temperature': 0.0})
      
      except ollama.ResponseError as e:
            if (e.status_code == 404):
                  raise ModelNotFoundError("Model không tồn tại. Hãy chạy lệnh 'ollama pull llama3.2'")
            raise InvalidResponseError("Response không hợp lệ")
      
      except httpx.ConnectError:
            raise AIModelOfflineException("Ollama mất kết nối") 
      
      except httpx.TimeoutException:
            raise RequestTimeoutError("Yêu cầu hết thời gian chờ")

      if response:
            if (isinstance(response, dict)):
                  msg = response.get("message")
            else:
                  msg = getattr(response, "message", None)

            if not msg:
                  raise InvalidResponseError("Response không hợp lệ")

            if (isinstance(msg, dict)):
                  content = msg.get("content")
            else:
                  content = getattr(msg, "content", None)

            if (isinstance(content, str)):
                  if not content or not content.strip():
                        raise InvalidResponseError("Response không hợp lệ")
                  else:
                        return content
            else:
                  raise InvalidResponseError("Response không hợp lệ")
      else:
            raise InvalidResponseError("Response không hợp lệ")


      