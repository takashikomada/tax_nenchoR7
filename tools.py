# tools.py
from typing import Dict, Any
import streamlit as st

import constants as ct
from utils import extract_page_numbers_from_sources, build_page_reference_text

from langchain_core.runnables import RunnableParallel, RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI


def ask_nentsu_qa(question: str) -> Dict[str, Any]:
    """年末調整の手引きに基づいて RAG で回答し、
    回答 + 参考ページ(P.xx) を返す（LangChain 0.2 対応版）
    """

    # initialize.py で作った retriever が前提
    retriever = st.session_state.get("retriever")
    if retriever is None:
        raise RuntimeError("retriever が初期化されていません（initialize.setup_retriever がまだ実行されていません）。")

    # LLM は呼ぶたびに生成（シンプルに）
    llm = ChatOpenAI(
        model=ct.LLM_MODEL,
        temperature=0.1,
    )

    # RAG チェーン（context + question を LLM に渡す）
    rag_chain = (
        {
            "context": retriever,
            "question": RunnablePassthrough(),
        }
        | ct.PROMPT_TEMPLATE
        | llm
        | StrOutputParser()
    )

    # 回答と docs（retriever の結果）を並列で取得
    parallel = RunnableParallel(
        answer=rag_chain,
        docs=retriever,
    )

    result = parallel.invoke(question)

    # 回答テキスト
    answer_text = result["answer"]

    # ドキュメントからページ番号を抽出
    docs = result["docs"]
    pages = extract_page_numbers_from_sources(docs)
    page_ref = build_page_reference_text(pages)

    # 最終的な表示用テキスト
    full_answer = f"{answer_text}\n\n{page_ref}"

    return {
        "answer": full_answer,
        "page_ref": page_ref,
    }
