# llm_client.py
from langchain_perplexity import ChatPerplexity
from config import PERPLEXITY_MODEL
import streamlit as st
my_key = st.secrets["PERPLEXITY_API_KEY"]
chat = ChatPerplexity(model=PERPLEXITY_MODEL, api_key=my_key)
