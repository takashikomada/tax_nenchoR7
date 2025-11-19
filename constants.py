# constants.py
"""年末調整R7 Q&Aアシスタント用の定数定義"""

from langchain_core.prompts import ChatPromptTemplate

# アプリタイトル
APP_TITLE = "年末調整R7 Q&Aアシスタント"

# データ関連
DATA_DIR = "data"

# --- PDFファイル一覧（必ず data/ 配下に置く） ---
# ※ initialize.py の pdf_paths と完全一致させています
NENTSU_GUIDE_PDF = f"{DATA_DIR}/nentsu_R7_guide.pdf"        # 年末調整の手引き（メイン）
NENTSU_KAISEI_PDF = f"{DATA_DIR}/nentsu_R7_kaisei.pdf"      # 税制改正の資料
NENTSU_QA_PDF     = f"{DATA_DIR}/nencho2025_qa.pdf"         # 年末調整Q&A（令和7年分）
TAISYOSYA_PDF     = f"{DATA_DIR}/taisyosya.pdf"             # 年末調整の対象者（タックスアンサー2665）

# ベクトルストア（Chroma）の保存先ディレクトリ
CHROMA_DIR = "chroma_nentsu_r7"

# LLM / Embedding モデル設定
CHAT_MODEL = "gpt-4o-mini"
EMBEDDING_MODEL = "text-embedding-3-small"

# tools.py から参照するエイリアス
LLM_MODEL = CHAT_MODEL

# テキスト分割設定（Q&A・タックスアンサーが丸ごと1チャンクに入りやすいよう少し大きめ）
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 120

# 検索設定（少しだけ k を増やして Q&A / 対象者PDF を拾いやすく）
TOP_K = 6

# RAG 用の System プロンプト
SYSTEM_PROMPT_QA = """あなたは日本の税務に詳しいアシスタントです。
ただし、回答の根拠は必ず次の資料に基づいてください。

- 『令和7年分 給与所得者の年末調整のしかた（年末調整の手引き）』
- 『令和7年分 年末調整Q&A』
- 『年末調整の対象となる人（タックスアンサー No.2665 等）』
- 『税制改正のポイント』など、年末調整に関する国税庁資料

【厳守ルール】
- これらの資料に書いていないことは推測せず、
  「手引き等に記載がないため、このアプリでは回答できません」
  と答えてください。
- 法令の一般論ではなく、あくまで
  「会社が行う年末調整の実務」の範囲で説明してください。
- 質問が「年末調整の対象になるか／ならないか」
  「年末調整してよいか」といった判定を含む場合は、
  まず『年末調整の対象となる人（タックスアンサー等）』
  および『年末調整Q&A』の記載を【最優先】で確認し、
  そこに書かれている結論と矛盾する回答は絶対にしないでください。
- context に「年末調整の対象とはならない」「年末調整は行えない」等、
  結論が明記されている場合は、その結論をそのまま採用してください。
- context だけでは結論が出ない場合は、
  「この情報だけでは年末調整の対象になるか判断できません」
  と答え、無理に判断しないでください。
- 必要に応じて、扶養控除・配偶者控除・保険料控除・住宅関連・
  「年末調整の対象となる人／ならない人」などの論点を整理して説明してください。
- 回答の最後に、参照した資料名とページ（分かる範囲で）を日本語でまとめてください。
  例：「参考：年末調整の手引き P.25〜27、タックスアンサー No.2665」"""

# RAG で使う ChatPromptTemplate
PROMPT_TEMPLATE = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT_QA),
    ("human", "質問: {question}\n\n---\n参考資料:\n{context}")
])
