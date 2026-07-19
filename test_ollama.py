# test_ollama.py

from langchain_ollama import OllamaLLM

# Create a connection to our local Ollama model
llm = OllamaLLM(model="llama3.1:8b")

# Send a prompt and get a response
response = llm.invoke("What is the capital of France? Reply in one word.")

print(response)##
