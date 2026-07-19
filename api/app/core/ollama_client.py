import ollama
import httpx
import asyncio
from ollama import AsyncClient

client = AsyncClient()

#Cấu hình OLLAMA Client
async def chat():
      try:
            await client.list()
      except Exception as e:
            print("Haven't opened OLLAMA yet!!!") 
            return False 
      
# Hàm Embedding (Biến chữ thành số)
async def generate_embedding(text: str):
      try:
            response = await client.embeddings(model = "nomic-embed-text", prompt = text)

            return response['embedding']
      except ollama.ResponseError as e:
            print('Error:', e.error)

            if (e.status_code == 404):
                  await client.pull(model="nomic-embed-text")
                  response = await client.embeddings(model = "nomic-embed-text", prompt = text)

                  return response['embedding']

      return None

# Hàm Chat (Sinh câu trả lời)
async def generate_chat(prompt: str):
      message = [{
            'role' : 'user',
            'content' : prompt
      }]
      try:
            response = await client.chat(model = "llama3.2", messages = message, options = {'temperature': 0.0})

            return response['message']['content'] 
      except ollama.ResponseError as e:
                  print('Error:', e.error)
                  if (e.status_code == 404):
                        await client.pull(model = "llama3.2")  
                        response = await client.chat(model = "llama3.2", messages = message, options = {'temperature': 0.0})
                        
                        return response['message']['content'] 
                  
      return None
                      

async def main():
      if (await chat() == False):
            return 

if __name__ == "__main__":
      asyncio.run(main())

      
