# 🚀 LLM API Testing Framework

---

RAG stands for Retrieval-Augmented Generation, an AI framework that enhances a Large Language Model's (LLM) capabilities by combining it with an external information retrieval system

---

This project is a **Streamlit-powered dashboard + CLI framework** for automated API testing using OpenAPI specifications.  
It generates test cases (headers, parameters, body validation, security checks, boundary tests) and validates responses with both **rule-based checks** and **LLM-based validation**.

---

## ✨ Features
- 📑 Parse OpenAPI spec and auto-generate test cases  
- 🛠️ API test execution (CLI or Streamlit UI)  
- ✅ Validations for:
  - Headers
  - Parameters
  - Body schema (required, types, enums, boundaries, combinations)
  - Security checks (e.g., `x-session-token`)  
- 🤖 LLM Validation (via [Perplexity API](https://docs.perplexity.ai))  
- 📊 CSV reports with pass/fail results  
- 💬 Knowledge Base Chat (ask questions against docs/PDFs)  

---

## 🗂 Project Structure
LLM-API-Testing/

│── app.py # Streamlit Dashboard

│── main.py # CLI Test Runner

│── config.py # Configurations (⚠️ don't commit secrets!)

│── requirements.txt # Python dependencies
│── README.md # Project documentation
├── openapi/ # OpenAPI loaders & helpers
├── tests/ # Test generators & executors
├── knowledgebase/ # Knowledge base loader

├── utils/ # Utility functions (file/text handling)
├── reports/ # Test execution CSV reports
└── testdata/ # API spec YAML/JSON files



---

## ⚙️ Installation
Clone the repo and install dependencies:

```bash
   pip install -r requirements.txt
```

Run with Streamlit Dashboard
```bash
  streamlit run app.py

```
Run with CLI

```bash
  python main.py --run-tests


```