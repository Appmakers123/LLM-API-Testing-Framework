import streamlit as st
import subprocess
import re
import pandas as pd
import os
import json
from config import CSV_OUTPUT, KNOWLEDGE_FOLDER, OPENAPI_YAML_PATH
from openapi.loader import load_openapi, pick_base_url
from openapi.operations import collect_operations

# Config
CSV_FILE = CSV_OUTPUT
KB_FOLDER = KNOWLEDGE_FOLDER

BASE_URL_OVERRIDE = None  # update if needed

st.set_page_config(page_title="🚀 API Test Dashboard", layout="wide")

import logging
from tornado.websocket import WebSocketClosedError

logging.getLogger("tornado.application").addFilter(
    lambda record: "WebSocketClosedError" not in record.getMessage()
)

# Colorize logs function (same as before)
def colorize_api_log(line):
    if "Response status" in line:
        status_match = re.search(r"Response status:\s*(\d+)", line)
        if status_match:
            status_code = int(status_match.group(1))
            if 200 <= status_code < 300:
                return f"<span style='color:limegreen;'>{line}</span>"
            elif 400 <= status_code < 500:
                return f"<span style='color:orange;'>{line}</span>"
            elif 500 <= status_code < 600:
                return f"<span style='color:red;'>{line}</span>"
    elif "[FAIL]" in line or "error" in line.lower():
        return f"<span style='color:red;'>{line}</span>"
    elif "[PASS]" in line:
        return f"<span style='color:limegreen;'>{line}</span>"
    return f"<span style='color:white;'>{line}</span>"

st.title("🚀 API Test Automation Dashboard")

tab1, tab2, tab3 = st.tabs([
    "1️⃣ Run API Tests",
    "2️⃣ View Test Cases",
    "3️⃣ Knowledge Base Chat"
])

# Load OpenAPI spec and operations once at start
@st.cache_data(show_spinner=False)
def load_apis():
    try:
        spec = load_openapi(OPENAPI_YAML_PATH)
        base_url = pick_base_url(spec, BASE_URL_OVERRIDE)
        operations = collect_operations(spec, base_url)
        return operations
    except Exception as e:
        st.error(f"Error loading OpenAPI spec: {e}")  # Show real error in UI
        return []

operations = load_apis()

with tab1:
    st.header("Select APIs to Run")
    st.write("Choose which APIs to run, then click 'Run API Tests'.")

    if not operations:
        st.error("Failed to load OpenAPI operations.")
    else:
        run_all = st.checkbox("Run All APIs", value=True)

        selected_indices = []
        if not run_all:
            api_display_list = [f"{i+1}. [{op['method'].upper()}] {op['path']}" for i, op in enumerate(operations)]
            selected_indices = st.multiselect(
                "Select APIs to run:",
                options=list(range(len(api_display_list))),
                format_func=lambda i: api_display_list[i],
            )
            if not selected_indices:
                st.warning("Select at least one API or check 'Run All APIs'.")

        logs_html = ""

        if st.button("▶ Run API Tests", type="primary"):
            st.info("Tests running... logs will appear below.")
            log_container = st.empty()

            ops_to_run = operations if run_all else [operations[i] for i in selected_indices]

            import tempfile
            import json as jsonlib

            # Save selected API paths to temp filter file
            with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
                jsonlib.dump([op["path"] for op in ops_to_run], f)
                filter_file_path = f.name

            command = ["python", "main.py", "--run-tests", "--filter-file", filter_file_path]

            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )

            line_count = 0
            for line in process.stdout:
                line = line.strip()
                if line:
                    styled_line = colorize_api_log(line)
                    logs_html += styled_line + "<br>"
                    line_count += 1

                # Update every 20 lines or on last line
                if line_count % 20 == 0:
                    try:
                        log_container.markdown(
                            f"<div style='height:400px;overflow:auto;background:#111;color:#eee;font-family:monospace;border-radius:8px;padding:10px;'>{logs_html}</div>",
                            unsafe_allow_html=True,
                        )
                    except Exception:
                        break

            process.wait()
            # Final update after process ends
            try:
                log_container.markdown(
                    f"<div style='height:400px;overflow:auto;background:#111;color:#eee;font-family:monospace;border-radius:8px;padding:10px;'>{logs_html}</div>",
                    unsafe_allow_html=True,
                )
            except Exception:
                pass

            if process.returncode != 0:
                error_output = process.stderr.read()
                st.error(f"❌ Test runner failed:\n{error_output}")
            else:
                st.success("✅ Tests completed successfully.")

with tab2:
    st.header("Generated Test Cases")

    if not os.path.exists(CSV_FILE):
        st.warning(f"No test results found at {CSV_FILE}. Please run the tests first.")
    else:
        df = pd.read_csv(CSV_FILE)

        if "TestStatus" in df.columns:
            status_list = ["All"] + sorted(df["TestStatus"].dropna().unique().tolist())
        else:
            status_list = ["All"]

        status_filter = st.selectbox("Filter by Test Status:", status_list)

        filtered_df = df if status_filter == "All" else df[df["TestStatus"] == status_filter]

        display_cols = [
            "Description", "Endpoint", "Method", "URL", "ExpectedStatus", "ActualStatus",
            "TestStatus", "ActualResponseSnippet", "LLMVerdict", "ElapsedSecs"
        ]
        display_cols = [col for col in display_cols if col in filtered_df.columns]

        st.dataframe(filtered_df[display_cols], width='stretch', height=300)

        test_case_index = st.number_input(
            "Select Test Case Row Number for Details:",
            min_value=0,
            max_value=len(filtered_df) - 1,
            value=0
        )

        test_case = filtered_df.iloc[test_case_index]

        st.subheader("Test Case Details")
        st.markdown("**Description:**")
        st.write(test_case.get("Description", ""))

        st.markdown("**Request Headers:**")
        try:
            st.json(json.loads(test_case.get("RequestHeaders", "{}")))
        except Exception:
            st.text(test_case.get("RequestHeaders", "{}"))

        st.markdown("**Request Body:**")
        try:
            if test_case.get("RequestBody"):
                parsed = json.loads(test_case["RequestBody"])
                st.json(parsed)
            else:
                st.text("No Request Body")
        except Exception:
            st.text(test_case.get("RequestBody", ""))

        st.markdown("**Actual Response Snippet:**")
        st.text(test_case.get("ActualResponseSnippet", ""))

        st.markdown(f"**Actual Status:** {test_case.get('ActualStatus', '')}")
        st.markdown(f"**Expected Status:** {test_case.get('ExpectedStatus', '')}")
        st.markdown(f"**Test Status:** {test_case.get('TestStatus', '')}")
        st.markdown(f"**LLM Verdict:** {test_case.get('LLMVerdict', '')}")
        st.markdown(f"**LLM Notes:** {test_case.get('LLMNotes', '')}")
        st.markdown(f"**Elapsed Time (secs):** {test_case.get('ElapsedSecs', '')}")

with tab3:
    st.header("Knowledge Base Chat (Multi-turn)")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Display chat messages with Streamlit chat_message
    for chat_msg in st.session_state.chat_history:
        role = chat_msg["role"]
        content = chat_msg["content"]
        with st.chat_message(role):
            st.markdown(content)

    # User input via chat_input box (appears at bottom fixed)
    if user_input := st.chat_input("Ask questions about the API or docs..."):
        try:
            from knowledgebase.kb_handler import KnowledgeBase
            from llm_client import chat

            kb = KnowledgeBase(KB_FOLDER)

            # Build KB query from all user messages + current input
            kb_query = " ".join(
                msg["content"] for msg in st.session_state.chat_history if msg["role"] == "user"
            ) + " " + user_input

            relevant_chunks = kb.query(kb_query)
            context_text = "\n---\n".join(relevant_chunks) if relevant_chunks else "No relevant knowledge base entries found."

            system_content = f"""
You are a helpful assistant specialized in APIs and troubleshooting.

Context from knowledge base:
{context_text}

Instructions:
- Use the context to answer the user's questions.
- If the context contains no answer, respond politely that information is not available in the knowledge base.
- Provide clear and concise explanations.
- Ask for clarifications if needed.
"""

            messages = [{"role": "system", "content": system_content}]
            for msg in st.session_state.chat_history:
                messages.append(msg)
            messages.append({"role": "user", "content": user_input})

            # Add user message to chat history and update UI immediately
            st.session_state.chat_history.append({"role": "user", "content": user_input})

            response = chat.invoke(messages)
            answer = response.content if hasattr(response, "content") else str(response)

            # Add assistant message to chat history
            st.session_state.chat_history.append({"role": "assistant", "content": answer})

            # Rerun to display updated chat history
            st.rerun()

        except Exception as e:
            st.error(f"Error during knowledge base chat: {e}")

    # Add a button to clear chat history if desired
    if st.button("Clear Chat"):
        st.session_state.chat_history = []
        st.rerun()
