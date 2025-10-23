"""Streamlit AI data analyst agent powered by the BigQuery MCP server."""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from enum import Enum
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


class LLMProvider(str, Enum):
    OPENAI = "OpenAI"
    ANTHROPIC = "Anthropic"
    GEMINI = "Gemini"


@dataclass
class LLMClientWrapper:
    provider: LLMProvider
    client: Any


@dataclass
class AgentConfig:
    base_url: str
    user_id: Optional[str]
    session_id: Optional[str]
    use_cache: bool
    maximum_bytes_billed: int
    row_limit: int
    model: str
    provider: LLMProvider


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

RESULT_PREVIEW_ROWS = 200
RESULT_DOWNLOAD_ROWS = 1000

DEFAULT_PROVIDER_NAME = os.getenv("LLM_PROVIDER", LLMProvider.OPENAI.value)
try:
    DEFAULT_PROVIDER = LLMProvider(DEFAULT_PROVIDER_NAME)
except ValueError:
    DEFAULT_PROVIDER = LLMProvider.OPENAI

PROVIDER_MODEL_DEFAULTS = {
    LLMProvider.OPENAI: os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
    LLMProvider.ANTHROPIC: os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514"),
    LLMProvider.GEMINI: os.getenv("GEMINI_MODEL", "gemini-1.5-pro-latest"),
}

PROVIDER_API_KEY_ENV_VARS = {
    LLMProvider.OPENAI: "OPENAI_API_KEY",
    LLMProvider.ANTHROPIC: "ANTHROPIC_API_KEY",
    LLMProvider.GEMINI: "GEMINI_API_KEY",
}

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


def split_system_and_conversation(
    messages: List[Dict[str, Any]],
) -> tuple[Optional[str], List[Dict[str, Any]]]:
    system_parts = [
        str(message.get("content", ""))
        for message in messages
        if message.get("role") == "system"
    ]
    system_prompt = "\n\n".join(part for part in system_parts if part) or None
    conversation = [message for message in messages if message.get("role") != "system"]
    return system_prompt, conversation


def initialise_llm_client(provider: LLMProvider, api_key: str) -> Optional[LLMClientWrapper]:
    api_key = (api_key or "").strip()
    if not api_key:
        return None

    if provider is LLMProvider.OPENAI:
        return LLMClientWrapper(provider=provider, client=OpenAI(api_key=api_key))

    if provider is LLMProvider.ANTHROPIC:
        try:
            from anthropic import Anthropic
        except ImportError as exc:  # pragma: no cover - dependency guard
            raise RuntimeError(
                "Anthropic client library is not installed. Please add the 'anthropic' dependency."
            ) from exc
        return LLMClientWrapper(provider=provider, client=Anthropic(api_key=api_key))

    if provider is LLMProvider.GEMINI:
        try:
            import google.generativeai as genai
        except ImportError as exc:  # pragma: no cover - dependency guard
            raise RuntimeError(
                "Google Generative AI client library is not installed."
                " Please add the 'google-generativeai' dependency."
            ) from exc
        genai.configure(api_key=api_key)
        return LLMClientWrapper(provider=provider, client=genai)

    raise RuntimeError(f"Unsupported LLM provider: {provider}")


def invoke_llm(
    llm_client: LLMClientWrapper,
    model: str,
    messages: List[Dict[str, Any]],
    temperature: float,
) -> str:
    provider = llm_client.provider

    if provider is LLMProvider.OPENAI:
        response = llm_client.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
        )
        if not response.choices:
            raise RuntimeError("OpenAI returned an empty response.")
        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("OpenAI returned an empty response.")
        return content

    system_prompt, conversation = split_system_and_conversation(messages)

    if provider is LLMProvider.ANTHROPIC:
        formatted_messages = []
        for message in conversation:
            role = message.get("role")
            if role not in {"user", "assistant"}:
                continue
            formatted_messages.append(
                {
                    "role": role,
                    "content": [
                        {
                            "type": "text",
                            "text": str(message.get("content", "")),
                        }
                    ],
                }
            )
        if not formatted_messages:
            formatted_messages = [
                {"role": "user", "content": [{"type": "text", "text": ""}]}
            ]

        response = llm_client.client.messages.create(
            model=model,
            temperature=temperature,
            max_output_tokens=4096,
            system=system_prompt,
            messages=formatted_messages,
        )
        text_parts = [
            block.text
            for block in getattr(response, "content", [])
            if getattr(block, "type", None) == "text" and getattr(block, "text", None)
        ]
        if not text_parts:
            raise RuntimeError("Anthropic returned an empty response.")
        return "\n".join(text_parts)

    if provider is LLMProvider.GEMINI:
        genai = llm_client.client
        model_client = genai.GenerativeModel(
            model_name=model,
            system_instruction=system_prompt or None,
        )

        contents = []
        for message in conversation:
            role = message.get("role")
            if role == "user":
                gemini_role = "user"
            elif role == "assistant":
                gemini_role = "model"
            else:
                continue
            contents.append(
                {
                    "role": gemini_role,
                    "parts": [{"text": str(message.get("content", ""))}],
                }
            )

        if not contents:
            contents = [{"role": "user", "parts": [{"text": ""}]}]

        response_kwargs: Dict[str, Any] = {}
        types_module = getattr(genai, "types", None)
        generation_config = None
        if types_module and hasattr(types_module, "GenerationConfig"):
            try:
                generation_config = types_module.GenerationConfig(temperature=temperature)
            except Exception:  # pragma: no cover - defensive
                generation_config = None
        if generation_config is not None:
            response_kwargs["generation_config"] = generation_config

        response = model_client.generate_content(
            contents,
            **response_kwargs,
        )
        text = getattr(response, "text", None)
        if text:
            return text

        candidates = getattr(response, "candidates", None) or []
        text_parts: List[str] = []
        for candidate in candidates:
            content = getattr(candidate, "content", None)
            parts = getattr(content, "parts", None) if content else None
            if not parts:
                continue
            for part in parts:
                if getattr(part, "text", None):
                    text_parts.append(part.text)
        if text_parts:
            return "\n".join(text_parts)

        raise RuntimeError("Gemini returned an empty response.")

    raise RuntimeError(f"Unsupported LLM provider: {provider}")


def generate_sql_plan(
    llm_client: LLMClientWrapper,
    model: str,
    question: str,
    metadata: Dict[str, Any],
    row_limit: int,
    conversation_history: Optional[List[Dict[str, Any]]] = None,
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
                "\n\n**IMPORTANT:** When the user refers to 'the table' or 'this table' without specifying a name,"
                " check the conversation history to identify which table was previously discussed."
                " Extract the full table reference (project.dataset.table) from previous queries or questions."
            ),
        },
    ]

    # Add conversation history for context, but limit to recent messages to avoid token limits
    if conversation_history:
        # Include the last 6 messages (3 exchanges) for context
        recent_history = conversation_history[-6:]
        for msg in recent_history:
            role = msg.get("role")
            if role == "user":
                messages.append({"role": "user", "content": msg.get("content", "")})
            elif role == "assistant":
                # For assistant messages, include the question context and SQL
                assistant_context = []
                if sql := msg.get("sql"):
                    assistant_context.append(f"Generated SQL:\n{sql}")
                if analysis := msg.get("analysis_steps"):
                    if isinstance(analysis, list):
                        assistant_context.append("Analysis: " + ", ".join(str(s) for s in analysis))
                if assistant_context:
                    messages.append({"role": "assistant", "content": "\n\n".join(assistant_context)})

    # Add current question with metadata
    messages.append({"role": "user", "content": json.dumps(prompt_payload, indent=2)})

    response = llm_client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.1,
    ).strip()
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
    llm_client: LLMClientWrapper,
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

    content = invoke_llm(
        llm_client=llm_client,
        model=model,
        messages=messages,
        temperature=0.2,
    )
    return content.strip()


def process_question(
    question: str,
    client: MCPTools,
    config: AgentConfig,
    metadata: Dict[str, Any],
    llm_client: Optional[OpenAI],
    conversation_history: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    plan: Dict[str, Any] = {}

    if not llm_client:
        raise RuntimeError(
            (
                f"The {config.provider.value} client is not initialised."
                " Provide a valid API key and ensure the SDK is installed."
            )
        )

    try:
        plan = generate_sql_plan(
            llm_client, config.model, question, metadata, config.row_limit, conversation_history
        )
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
provider_options = list(LLMProvider)
default_provider_index = 0
if DEFAULT_PROVIDER in provider_options:
    default_provider_index = provider_options.index(DEFAULT_PROVIDER)
selected_provider = st.sidebar.selectbox(
    "LLM provider",
    options=provider_options,
    index=default_provider_index,
    format_func=lambda option: option.value,
)

api_key_env_var = PROVIDER_API_KEY_ENV_VARS.get(selected_provider, "OPENAI_API_KEY")
api_key_label = f"{selected_provider.value} API key"
api_key_help = (
    f"Required for using {selected_provider.value} to translate questions into SQL"
    " and to summarise results."
)
provider_api_key = st.sidebar.text_input(
    api_key_label,
    value=os.getenv(api_key_env_var, ""),
    type="password",
    help=api_key_help,
    key=f"{selected_provider.value.lower()}-api-key",
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

model_default = PROVIDER_MODEL_DEFAULTS.get(selected_provider, "")
model_label = f"{selected_provider.value} model"
model_help = f"{selected_provider.value} model used for SQL planning and summaries."
model_name = st.sidebar.text_input(
    model_label,
    value=model_default,
    help=model_help,
    key=f"{selected_provider.value.lower()}-model",
)

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
    provider=selected_provider,
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
llm_client_error: Optional[str] = None
llm_client: Optional[LLMClientWrapper] = None
try:
    llm_client = initialise_llm_client(selected_provider, provider_api_key)
except RuntimeError as exc:  # pragma: no cover - dependency guard
    llm_client_error = str(exc)

if llm_client_error:
    st.sidebar.error(llm_client_error)
elif llm_client is None:
    st.sidebar.warning(
        f"Provide a valid {selected_provider.value} API key to enable SQL planning and summaries."
    )
    st.info(f"Add a {selected_provider.value} API key in the sidebar to activate the AI analyst.")

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
                    conversation_history=st.session_state["conversation"],
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
