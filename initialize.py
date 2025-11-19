# initialize.py
"""RAG 用ベクトルストアの初期化処理"""

import os
import streamlit as st

from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma

import constants as ct


def _load_guide_documents():
    """data フォルダ内の PDF（4種）を読み込む"""

    pdf_paths = [
        ct.NENTSU_GUIDE_PDF,    # 年末調整の手引き
        ct.NENTSU_QA_PDF,       # 年末調整Q&A（令和7年版）
        ct.NENTSU_KAISEI_PDF,   # 改正のポイント
        ct.TAISYOSYA_PDF,       # 年末調整の対象者（タックスアンサー2665）
    ]

    documents = []
    for path in pdf_paths:
        if not os.path.exists(path):
            print(f"[WARN] PDF が見つかりません: {path}")
            continue

        loader = PyMuPDFLoader(path)
        docs = loader.load()

        # どの資料・何ページかをメタデータとして保持
        for d in docs:
            src = os.path.basename(path)
            page = d.metadata.get("page")

            d.metadata["source"] = src
            if page is not None:
                d.metadata["page"] = int(page) + 1  # 1 始まりに統一

        documents.extend(docs)

    return documents


def _split_documents(documents):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=ct.CHUNK_SIZE,
        chunk_overlap=ct.CHUNK_OVERLAP,
        separators=["\n\n", "\n", "。", "、", " "],
    )
    return splitter.split_documents(documents)


def _build_vectorstore():
    docs = _load_guide_documents()
    if not docs:
        raise RuntimeError(
            "参照用PDFが1つも読み込めませんでした。data フォルダを確認してください。"
        )

    chunks = _split_documents(docs)
    embeddings = OpenAIEmbeddings(model=ct.EMBEDDING_MODEL)

    vs = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=ct.CHROMA_DIR,
    )
    return vs


def get_vectorstore():
    if os.path.exists(ct.CHROMA_DIR) and os.listdir(ct.CHROMA_DIR):
        embeddings = OpenAIEmbeddings(model=ct.EMBEDDING_MODEL)
        vs = Chroma(
            embedding_function=embeddings,
            persist_directory=ct.CHROMA_DIR,
        )
    else:
        vs = _build_vectorstore()

    return vs


def setup_retriever():
    if "retriever" in st.session_state:
        return

    vs = get_vectorstore()
    retriever = vs.as_retriever(search_kwargs={"k": ct.TOP_K})
    st.session_state["retriever"] = retriever
