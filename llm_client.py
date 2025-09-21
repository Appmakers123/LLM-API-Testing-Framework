# llm_client.py
from langchain_perplexity import ChatPerplexity
from config import PERPLEXITY_MODEL, PERPLEXITY_API_KEY

chat = ChatPerplexity(model=PERPLEXITY_MODEL, api_key=PERPLEXITY_API_KEY)
