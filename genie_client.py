"""Thin wrapper around the Databricks Genie Conversation API (databricks-sdk).

ask() starts a new conversation, or continues one when you pass the previous conversation_id,
and returns a plain dict the UI can render:
    {"conversation_id", "text": [..], "sql", "sql_description", "df", "suggestions": [..], "error"}
"""
from __future__ import annotations

from datetime import timedelta

import pandas as pd
import streamlit as st
from databricks.sdk.service.dashboards import MessageStatus

from data import get_client, statement_to_df

GENIE_TIMEOUT = timedelta(minutes=3)
MAX_ROWS_SHOWN = 500


def ask(question: str, conversation_id: str | None = None) -> dict:
    w = get_client()
    space_id = st.secrets["GENIE_SPACE_ID"]
    out = {"conversation_id": conversation_id, "text": [], "sql": None, "sql_description": None,
           "df": None, "suggestions": [], "error": None}
    try:
        if conversation_id is None:
            msg = w.genie.start_conversation_and_wait(space_id, question, timeout=GENIE_TIMEOUT)
        else:
            msg = w.genie.create_message_and_wait(space_id, conversation_id, question, timeout=GENIE_TIMEOUT)
    except Exception as exc:  # network, timeout, rate limit, permission
        out["error"] = f"Genie could not answer this question ({type(exc).__name__}: {exc})"
        return out

    out["conversation_id"] = msg.conversation_id
    if msg.status == MessageStatus.FAILED or msg.error:
        detail = msg.error.error if msg.error and msg.error.error else "unknown error"
        out["error"] = f"Genie could not answer this question: {detail}"
        return out

    message_id = msg.message_id or msg.id
    for att in msg.attachments or []:
        if att.text and att.text.content:
            out["text"].append(att.text.content)
        if att.suggested_questions and att.suggested_questions.questions:
            out["suggestions"] = list(att.suggested_questions.questions)
        if att.query and att.query.query:
            out["sql"] = att.query.query
            out["sql_description"] = att.query.description
            try:
                res = w.genie.get_message_attachment_query_result(
                    space_id, msg.conversation_id, message_id, att.attachment_id)
                df = statement_to_df(res.statement_response)
                out["df"] = df.head(MAX_ROWS_SHOWN) if isinstance(df, pd.DataFrame) else None
            except Exception as exc:
                out["error"] = f"Genie wrote the query but the result could not be fetched ({type(exc).__name__})."
    return out
