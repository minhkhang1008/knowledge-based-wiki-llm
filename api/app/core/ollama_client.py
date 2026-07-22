import ollama
import httpx
import asyncio
from ollama import AsyncClient

client = AsyncClient()

class OLLAMA_Connection(Exception):
      # Bắt lỗi chưa bật OLLAMA
      pass

class Request_Timeout(Exception):
      # Bắt lỗi Timeout
      pass

class Inexist_Model(Exception):
      # Bắt lỗi Model hong tồn tại
      pass

class Response_Error(Exception):
      # Bắt lỗi response hong hợp lệ
      pass

#Cấu hình OLLAMA Client
async def chat():
      try:
            await client.list()
      except Exception as e:
            raise OLLAMA_Connection("Chưa mở Ollama")
      
# Hàm Embedding (Biến chữ thành số)
async def generate_embedding(text: str) -> list[float]:
      try:
            response = await client.embeddings(model = "nomic-embed-text", prompt = text)

            if (response["embedding"] == [] or response["embedding"] == None):
                  raise Response_Error("Response không hợp lệ")
            
            return response['embedding']
      
      except ollama.ResponseError as e:
            if (e.status_code == 404):
                  raise Inexist_Model("Model không tồn tại. Hãy chạy lệnh 'ollama run nomic-embed-text'")
            
            raise Response_Error("Response không hợp lệ")
            
      except httpx.ConnectError:
            raise OLLAMA_Connection("Ollama mất kết nối") 
            
      except httpx.TimeoutException:
            raise Request_Timeout("Yêu cầu hết thời gian chờ")

# Hàm Chat (Sinh câu trả lời)
async def generate_chat(prompt: str) -> str:
      message = [{
            'role' : 'user',
            'content' : prompt
      }]
      try:
            response = await client.chat(model = "llama3.2", messages = message, options = {'temperature': 0.0})
            content = response['message']['content']

            if (content == "" or content == None):
                  raise Response_Error("Response không hợp lệ")
            
            return content 
      
      except ollama.ResponseError as e:
            if (e.status_code == 404):
                  raise Inexist_Model("Model không tồn tại. Hãy chạy lệnh 'ollama run llama3.2'")
            raise Response_Error("Response không hợp lệ")
      
      except httpx.ConnectError:
            raise OLLAMA_Connection("Ollama mất kết nối") 
      
      except httpx.TimeoutException:
            raise Request_Timeout("Yêu cầu hết thời gian chờ")
      
                      

async def main():
      await chat()

if __name__ == "__main__":
      asyncio.run(main())

      
