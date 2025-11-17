
# utils.py
"""共通ユーティリティ関数群"""

from typing import List, Dict, Any
from langchain_openai import ChatOpenAI
import constants as ct

def get_llm():
    """ChatOpenAI のインスタンスを返すヘルパー関数。"""
    return ChatOpenAI(
        model=ct.CHAT_MODEL,
        temperature=0.1,
    )

def extract_page_numbers_from_sources(sources: List[Any]) -> List[int]:
    """LangChain の source_documents からページ番号（0始まり）を取り出し、1始まりに変換して一意なリストで返す。"""
    pages = []
    for doc in sources:
        meta = getattr(doc, "metadata", {}) or {}
        page = meta.get("page")
        if isinstance(page, int):
            pages.append(page + 1)  # PDF のページは 1 始まりで見せる
    # 重複を消してソート
    return sorted(set(pages))

def build_page_reference_text(pages: List[int]) -> str:
    """ページ番号リストから「参考：年末調整の手引き P.xx, P.yy」形式の文字列を作る。"""
    if not pages:
        return "参考：年末調整の手引き（該当ページ番号の特定ができませんでした）"
    joined = ", ".join(f"P.{p}" for p in pages)
    return f"参考：年末調整の手引き {joined}"
