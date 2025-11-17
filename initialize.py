"""RAG 用ベクトルストアの初期化処理"""

import os
import streamlit as st
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma

import constants as ct


def _load_guide_documents():
    """年末調整の手引き PDF および関連資料からドキュメントを読み込む。"""

    # メインとなる年末調整の手引き（必須）
    main_pdf_path = ct.NENTSU_GUIDE_PDF

    # 追加資料：令和7年度税制改正Q&A など（存在すれば読み込む）
    # data/ 配下に "nentsu_R7_kaisei.pdf" が置いてある前提
    extra_pdf_paths = [
        "data/nentsu_R7_kaisei.pdf",
    ]

    if not os.path.exists(main_pdf_path):
        raise FileNotFoundError(
            f"PDF が見つかりませんでした。'{main_pdf_path}' にファイルを配置してください。"
        )

    docs = []

    # メインPDF読み込み
    main_loader = PyMuPDFLoader(main_pdf_path)
    main_docs = main_loader.load()
    for d in main_docs:
        d.metadata.setdefault("source", os.path.basename(main_pdf_path))
    docs.extend(main_docs)

    # 追加PDFがあれば読み込み
    for path in extra_pdf_paths:
        if not os.path.exists(path):
            # サブ資料がない場合は警告だけ出してスキップ
            st.warning(
                f"追加資料 '{path}' が見つからなかったため、このPDFは検索対象に含まれません。"
            )
            continue

        loader = PyMuPDFLoader(path)
        extra_docs = loader.load()
        for d in extra_docs:
            d.metadata.setdefault("source", os.path.basename(path))
        docs.extend(extra_docs)

    return docs


def _build_vectorstore():
    """PDF からベクトルストアを新規構築する。"""
    docs = _load_guide_documents()
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=ct.CHUNK_SIZE,
        chunk_overlap=ct.CHUNK_OVERLAP,
        separators=["\n\n", "\n", "。", "、", " "],
    )
    splits = splitter.split_documents(docs)
    embeddings = OpenAIEmbeddings(model=ct.EMBEDDING_MODEL)
    vs = Chroma.from_documents(
        splits,
        embedding=embeddings,
        persist_directory=ct.CHROMA_DIR,
    )
    return vs


def get_vectorstore():
    """既存のベクトルストアを読み込む。なければ新規構築する。"""
    embeddings = OpenAIEmbeddings(model=ct.EMBEDDING_MODEL)
    if os.path.exists(ct.CHROMA_DIR):
        vs = Chroma(
            embedding_function=embeddings,
            persist_directory=ct.CHROMA_DIR,
        )
    else:
        vs = _build_vectorstore()
    return vs


def setup_retriever():
    """Streamlit セッション上に retriever をセットする。"""
    if "retriever" in st.session_state:
        return
    vs = get_vectorstore()
    retriever = vs.as_retriever(search_kwargs={"k": ct.TOP_K})
    st.session_state["retriever"] = retriever
