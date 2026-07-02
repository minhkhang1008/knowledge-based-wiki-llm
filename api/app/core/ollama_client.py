import ollama
import httpx
import asyncio
from ollama import AsyncClient

client = AsyncClient()

#Cấu hình OLLAMA Client
async def chat():
      try:
            await client.list()
      except:
            print("Haven't opened OLLAMA yet!!!") 

# Hàm Embedding (Biến chữ thành số)
async def generate_embedding(text: str):
      try:
            response = await AsyncClient().embeddings(model="nomic-embed-text", prompt=text)

            return response['embedding']
      except ollama.ResponseError as e:
            print('Error:', e.error)
            if (e.status_code == 404):
                  await AsyncClient().pull(model="nomic-embed-text")

# Hàm Chat (Sinh câu trả lời)
async def generate_chat(prompt: str):
      message = [{
            'role' : 'user',
            'content' : prompt
      }]
      try:
            response = await AsyncClient().chat(model = "llama3.2:1b", messages = message, temperature = 0.1)

            return response['message']['content'] 
      except ollama.ResponseError as e:
                  print('Error:', e.error)
                  if (e.status_code == 404):
                        await AsyncClient().pull(model = "llama3.2:1b")  
                        response = await AsyncClient().chat(model = "llama3.2:1b", messages = message, temperature = 0.1)
                        
                        return response['message']['content'] 
                      

async def main():
      await chat()

if __name__ == "__main__":
      asyncio.run(main())

      
