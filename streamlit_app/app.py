"""Streamlit AI data analyst agent powered by the BigQuery MCP server."""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st
from openai import OpenAI
from requests.exceptions import RequestException

# Ensure the repository root is on the Python path so we can import ai_agent modules
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))

from ai_agent.agent_core.system_message import SYSTEM_MESSAGE
from ai_agent.data_models.query_result import QueryResult
from ai_agent.tool_interface.mcp_tools import MCPTools
from ai_agent.utils.error_handler import handle_mcp_error

# -----------------------------------------------------------------------------
# Configuration data structures
# -----------------------------------------------------------------------------


@dataclass
class AgentConfig:
    base_url: str
    user_id: Optional[str]
    session_id: Optional[str]
    use_cache: bool
    maximum_bytes_billed: int
    row_limit: int
    model: str


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

RESULT_PREVIEW_ROWS = 200
RESULT_DOWNLOAD_ROWS = 1000
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
DEFAULT_BASE_URL = os.getenv("MCP_BIGQUERY_BASE_URL", "http://localhost:8005")
DEFAULT_SESSION_ID = os.getenv("MCP_SESSION_ID", "streamlit-session")
DEFAULT_USER_ID = os.getenv("MCP_USER_ID")


# -----------------------------------------------------------------------------
# Helper functions
# -----------------------------------------------------------------------------


def normalise_base_url(url: str) -> str:
    url = url.strip() or DEFAULT_BASE_URL
    if url.endswith("/"):
        url = url[:-1]
    return url


def parse_json_response(raw_text: str) -> Dict[str, Any]:
    """Parse JSON from an LLM response, recovering from light formatting."""
    raw_text = (raw_text or "").strip()
    if not raw_text:
        raise ValueError("Empty response from LLM")

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        pass

    # Attempt to recover by extracting the first JSON object or array
    start = raw_text.find("{")
    end = raw_text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(raw_text[start : end + 1])
        except json.JSONDecodeError:
            pass

    raise ValueError("LLM response was not valid JSON")


def ensure_limit_clause(sql: str, row_limit: int) -> str:
    """Ensure the SQL query contains a LIMIT clause to control costs."""
    if row_limit <= 0:
        return sql

    lower_sql = sql.lower()
    if "limit" in lower_sql:
        return sql

    trimmed = sql.rstrip().rstrip(";")
    return f"{trimmed}\nLIMIT {row_limit};"


def load_table_schema(client: MCPTools, dataset_id: str, table_id: str) -> Dict[str, Any]:
    """Retrieve schema metadata for a table, handling API errors gracefully."""
    try:
        response = client.get_table_schema(dataset_id=dataset_id, table_id=table_id)
    except RequestException as exc:  # pragma: no cover - UI feedback
        raise RuntimeError(handle_mcp_error(exc)) from exc

    if "error" in response:
        raise RuntimeError(response.get("error"))

    schema = response.get("schema", [])
    column_docs = response.get("column_documentation")
    if column_docs:
        # Merge documentation into schema entries when possible
        doc_map = {doc.get("column_name"): doc for doc in column_docs}
        for column in schema:
            column_name = column.get("name")
            if column_name in doc_map:
                column["documentation"] = doc_map[column_name]
    return {"schema": schema, "metadata": {k: v for k, v in response.items() if k not in {"schema", "column_documentation"}}}


def build_metadata_payload(
    available_datasets: List[str],
    selected_dataset: Optional[str],
    table_schemas: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "available_datasets": available_datasets,
        "selected_dataset": selected_dataset,
        "table_schemas": table_schemas,
    }


def initialise_openai_client(api_key: str) -> Optional[OpenAI]:
    api_key = api_key.strip()
    if not api_key:
        return None
    return OpenAI(api_key=api_key)


def generate_sql_plan(
    llm_client: OpenAI,
    model: str,
    question: str,
    metadata: Dict[str, Any],
    row_limit: int,
) -> Dict[str, Any]:
    prompt_payload = {
        "question": question,
        "metadata": metadata,
        "guidelines": {
            "row_limit": row_limit,
            "dialect": "BigQuery Standard SQL",
            "safety": "Read-only queries only. Do not perform DML/DDL operations.",
        },
        "expected_response_schema": {
            "sql": "Required. Read-only SQL query or null if impossible.",
            "analysis_steps": "Ordered list describing how the query answers the question.",
            "assumptions": "List of assumptions or clarifications you made.",
            "follow_up_questions": "Optional list of follow-up suggestions for the user.",
            "confidence": "Float between 0 and 1 describing confidence in the analysis.",
        },
    }

    messages = [
        {
            "role": "system",
            "content": (
                "You are an expert BigQuery data analyst."
                " Use the provided metadata and follow the MCP BigQuery server guidelines below.\n\n"
                f"Guidelines:\n{SYSTEM_MESSAGE}\n\n"
                "Return a single JSON object that follows the expected schema."
                " Keep SQL efficient and readable. Always include a LIMIT clause no higher than the requested limit"
                " unless the user explicitly requests otherwise."
            ),
        },
        {"role": "user", "content": json.dumps(prompt_payload, indent=2)},
    ]

    response = llm_client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.1,
    )
    content = response.choices[0].message.content or ""
    return parse_json_response(content)


def basic_summary(question: str, result_preview: List[Dict[str, Any]]) -> str:
    if not result_preview:
        return (
            "I ran the query but BigQuery did not return any rows for this question."
            " You might want to broaden the filters or verify that data exists for the requested period."
        )

    column_names = list(result_preview[0].keys())
    preview_count = len(result_preview)
    columns_formatted = ", ".join(column_names)
    return (
        f"I ran a query to answer: **{question}**.\n\n"
        f"Here are the first {preview_count} rows returned."
        f" The dataset includes the following columns: {columns_formatted}."
    )


def generate_summary(
    llm_client: OpenAI,
    model: str,
    question: str,
    sql: str,
    result_preview: List[Dict[str, Any]],
    statistics: Dict[str, Any],
    cached: bool,
    plan: Dict[str, Any],
) -> str:
    payload = {
        "question": question,
        "sql": sql,
        "result_preview": result_preview,
        "statistics": statistics,
        "cached": cached,
        "plan": plan,
    }

    messages = [
        {
            "role": "system",
            "content": (
                "You are an expert data analyst."
                " Craft a concise Markdown answer summarising the query results."
                " Include an executive summary, explain key findings, and reference the SQL when useful."
                " Mention whether the result came from cache when appropriate."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(payload, indent=2),
        },
    ]

    response = llm_client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.2,
    )
    return (response.choices[0].message.content or "").strip()


def process_question(
    question: str,
    client: MCPTools,
    config: AgentConfig,
    metadata: Dict[str, Any],
    llm_client: Optional[OpenAI],
) -> Dict[str, Any]:
    plan: Dict[str, Any] = {}

    if not llm_client:
        raise RuntimeError("An OpenAI API key is required to generate SQL and summaries.")

    try:
        plan = generate_sql_plan(llm_client, config.model, question, metadata, config.row_limit)
    except Exception as exc:
        raise RuntimeError(f"Failed to generate SQL plan: {exc}") from exc

    sql = plan.get("sql")
    if not sql:
        explanation = plan.get("analysis_steps") or plan.get("assumptions") or "No SQL was produced."
        raise RuntimeError(
            "The LLM could not generate a valid SQL statement for this question. "
            f"Details: {explanation}"
        )

    sql_with_limit = ensure_limit_clause(sql, config.row_limit)

    try:
        raw_response = client.execute_bigquery_sql(
            sql=sql_with_limit,
            maximum_bytes_billed=config.maximum_bytes_billed,
            use_cache=config.use_cache,
            user_id=config.user_id or None,
            session_id=config.session_id or None,
        )
    except RequestException as exc:
        raise RuntimeError(handle_mcp_error(exc)) from exc

    query_result = QueryResult.from_mcp_response(raw_response)
    if query_result.is_error:
        raise RuntimeError(query_result.error or "Unknown error executing query.")

    full_rows = query_result.result or []
    preview_rows = full_rows[:RESULT_PREVIEW_ROWS]
    downloadable_rows = full_rows[:RESULT_DOWNLOAD_ROWS]

    statistics = {
        "totalRows": query_result.statistics.totalRows,
        "totalBytesProcessed": query_result.statistics.totalBytesProcessed,
        "duration_ms": query_result.statistics.duration_ms,
        "started": query_result.statistics.started,
        "ended": query_result.statistics.ended,
        "cached_at": query_result.cached_at,
    }

    summary_text = basic_summary(question, preview_rows)
    if llm_client:
        try:
            summary_text = generate_summary(
                llm_client=llm_client,
                model=config.model,
                question=question,
                sql=sql_with_limit,
                result_preview=preview_rows,
                statistics=statistics,
                cached=query_result.cached,
                plan=plan,
            )
        except Exception as exc:  # pragma: no cover - UI feedback
            summary_text = basic_summary(question, preview_rows) + f"\n\nLLM summary failed: {exc}"

    return {
        "role": "assistant",
        "content": summary_text,
        "sql": sql_with_limit,
        "analysis_steps": plan.get("analysis_steps"),
        "assumptions": plan.get("assumptions"),
        "follow_ups": plan.get("follow_up_questions"),
        "confidence": plan.get("confidence"),
        "statistics": statistics,
        "cached": query_result.cached,
        "preview_rows": preview_rows,
        "download_rows": downloadable_rows,
        "has_more_rows": len(full_rows) > len(preview_rows),
    }


def render_assistant_message(message: Dict[str, Any], key: Optional[str] = None) -> None:
    if error := message.get("error"):
        st.error(error)
        return

    widget_key = key or str(id(message))
    suffix_label = f" · run {widget_key}" if key else ""

    st.markdown(message.get("content", ""))

    if message.get("analysis_steps"):
        steps = message["analysis_steps"]
        if isinstance(steps, list):
            formatted_steps = "\n".join(f"- {step}" for step in steps if step)
        else:
            formatted_steps = str(steps)
        with st.expander(f"Analysis plan{suffix_label}"):
            st.markdown(formatted_steps)

    if assumptions := message.get("assumptions"):
        if isinstance(assumptions, list):
            assumptions_text = "\n".join(f"- {assumption}" for assumption in assumptions if assumption)
        else:
            assumptions_text = str(assumptions)
        with st.expander(f"Assumptions & clarifications{suffix_label}"):
            st.markdown(assumptions_text)

    if follow_ups := message.get("follow_ups"):
        if isinstance(follow_ups, list):
            follow_ups_text = "\n".join(f"- {item}" for item in follow_ups if item)
        else:
            follow_ups_text = str(follow_ups)
        with st.expander(f"Suggested follow-up questions{suffix_label}"):
            st.markdown(follow_ups_text)

    stats = message.get("statistics") or {}
    if stats:
        col1, col2, col3 = st.columns(3)
        if stats.get("totalRows") is not None:
            col1.metric("Rows returned", f"{stats['totalRows']:,}")
        if stats.get("totalBytesProcessed") is not None:
            bytes_processed = stats["totalBytesProcessed"] or 0
            col2.metric("Bytes processed", f"{bytes_processed:,}")
        cached_label = "Yes" if message.get("cached") else "No"
        col3.metric("Cached result", cached_label)

        with st.expander(f"Query statistics{suffix_label}"):
            st.json(stats)

    preview_rows = message.get("preview_rows") or []
    if preview_rows:
        st.subheader("Result preview")
        df_preview = pd.DataFrame(preview_rows)
        st.dataframe(df_preview, use_container_width=True)

        download_rows = message.get("download_rows") or []
        if download_rows:
            df_download = pd.DataFrame(download_rows)
            csv_bytes = df_download.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="Download results as CSV (preview)",
                data=csv_bytes,
                file_name="query_results.csv",
                mime="text/csv",
                key=f"download-{widget_key}",
            )

        if message.get("has_more_rows"):
            st.info(
                "Showing the first preview rows only. Refine the query with additional filters "
                "or download the data for a deeper analysis."
            )
    else:
        st.info("The query completed successfully but returned no rows.")

    if sql := message.get("sql"):
        with st.expander(f"SQL query executed{suffix_label}"):
            st.code(sql, language="sql")


# -----------------------------------------------------------------------------
# Streamlit application layout
# -----------------------------------------------------------------------------


st.set_page_config(page_title="MCP BigQuery AI Analyst", layout="wide")
st.title("🚀 MCP BigQuery AI Analyst")
st.caption(
    "Ask natural language questions about your BigQuery data."
    " The assistant uses the MCP BigQuery server to plan and run safe, cost-aware SQL queries."
)

st.sidebar.header("Agent configuration")
openai_api_key = st.sidebar.text_input(
    "OpenAI API key",
    value=os.getenv("OPENAI_API_KEY", ""),
    type="password",
    help="Required for translating questions into SQL and summarising results.",
)

base_url_input = st.sidebar.text_input(
    "MCP server base URL",
    value=DEFAULT_BASE_URL,
    help="HTTP endpoint where the MCP BigQuery server is running.",
)

use_cache = st.sidebar.checkbox("Use cached results when available", value=True)
row_limit = st.sidebar.slider("Default LIMIT for exploratory queries", 10, 1000, 200, step=10)
maximum_bytes = st.sidebar.number_input(
    "Maximum bytes billed per query",
    min_value=1_000_000,
    value=100_000_000,
    step=1_000_000,
    help="Protects against expensive scans. Increase if your queries legitimately need more data.",
)

model_name = st.sidebar.text_input("OpenAI model", value=DEFAULT_MODEL, help="Model used for SQL planning and summarisation.")
user_id_input = st.sidebar.text_input("User ID (optional)", value=DEFAULT_USER_ID or "")
session_id_input = st.sidebar.text_input("Session ID", value=DEFAULT_SESSION_ID)

base_url = normalise_base_url(base_url_input)
agent_config = AgentConfig(
    base_url=base_url,
    user_id=user_id_input or None,
    session_id=session_id_input or None,
    use_cache=use_cache,
    maximum_bytes_billed=maximum_bytes,
    row_limit=row_limit,
    model=model_name,
)

client = MCPTools(base_url=agent_config.base_url)

try:
    datasets_response = client.get_datasets()
    if "error" in datasets_response:
        raise RuntimeError(datasets_response.get("error"))
    datasets = [item.get("dataset_id") for item in datasets_response.get("datasets", []) if item.get("dataset_id")]
except RequestException as exc:
    datasets = []
    st.sidebar.error(f"Failed to load datasets: {handle_mcp_error(exc)}")
except RuntimeError as exc:
    datasets = []
    st.sidebar.error(f"Failed to load datasets: {exc}")

selected_dataset = None
selected_tables: List[str] = []
table_schemas: Dict[str, Any] = {}

if datasets:
    dataset_options = ["(none)"] + datasets
    chosen_dataset = st.sidebar.selectbox(
        "Dataset (optional)",
        options=dataset_options,
        help="Select a dataset to fetch table schemas for better SQL generation.",
    )
    if chosen_dataset != "(none)":
        selected_dataset = chosen_dataset

if selected_dataset:
    try:
        tables_response = client.get_tables(selected_dataset)
        if "error" in tables_response:
            raise RuntimeError(tables_response.get("error"))
        table_options = [item.get("table_id") for item in tables_response.get("tables", []) if item.get("table_id")]
    except RequestException as exc:
        table_options = []
        st.sidebar.error(f"Failed to load tables: {handle_mcp_error(exc)}")
    except RuntimeError as exc:
        table_options = []
        st.sidebar.error(f"Failed to load tables: {exc}")
    selected_tables = st.sidebar.multiselect(
        "Tables to include in context (optional)",
        options=table_options,
        default=table_options[:1] if table_options else [],
        help="Schemas for selected tables are shared with the LLM to improve SQL quality.",
    )

    for table_id in selected_tables:
        try:
            table_schemas[table_id] = load_table_schema(client, selected_dataset, table_id)
        except RuntimeError as exc:
            st.sidebar.warning(f"Failed to load schema for {table_id}: {exc}")
else:
    if datasets:
        st.sidebar.info("Select a dataset to share schema context with the agent.")
    else:
        st.sidebar.info("No datasets available or the MCP server is unreachable.")

metadata_payload = build_metadata_payload(datasets, selected_dataset, table_schemas)
llm_client = initialise_openai_client(openai_api_key)
if llm_client is None:
    st.sidebar.warning("Enter a valid OpenAI API key to enable SQL planning and summaries.")
    st.info("Add your OpenAI API key in the sidebar to activate the AI analyst.")

if "conversation" not in st.session_state:
    st.session_state["conversation"] = []

assistant_counter = 0
for msg in st.session_state["conversation"]:
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant":
            assistant_counter += 1
            msg.setdefault("message_key", str(assistant_counter))
            render_assistant_message(msg, key=msg["message_key"])
        else:
            st.markdown(msg.get("content", ""))

prompt = st.chat_input("Ask your data question…")

if prompt:
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state["conversation"].append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        with st.spinner("Analyzing data with the MCP BigQuery agent…"):
            try:
                message = process_question(
                    question=prompt,
                    client=client,
                    config=agent_config,
                    metadata=metadata_payload,
                    llm_client=llm_client,
                )
            except RuntimeError as exc:
                message = {"role": "assistant", "error": str(exc), "content": f"❌ {exc}"}

            assistant_runs = sum(1 for item in st.session_state["conversation"] if item["role"] == "assistant")
            message_key = str(assistant_runs + 1)
            message["message_key"] = message_key
            render_assistant_message(message, key=message_key)
            st.session_state["conversation"].append(message)

st.sidebar.markdown("---")
st.sidebar.markdown(
    "**Tips:**\n"
    "- Ensure the MCP server is running and accessible.\n"
    "- Provide table schemas for best SQL generation.\n"
    "- Use user/session identifiers to take advantage of caching and personalised preferences."
)
