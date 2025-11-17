
# constants.py
"""年末調整R7 Q&Aアシスタント用の定数定義"""

APP_TITLE = "年末調整R7 Q&Aアシスタント"

# データ関連
DATA_DIR = "data"
# 必ず data/ 配下にこの名前で PDF を置いてください
NENTSU_GUIDE_PDF = "data/nentsu_R7_guide.pdf"

# ベクトルストア（Chroma）の保存先ディレクトリ
CHROMA_DIR = "chroma_nentsu_r7"

# LLM / Embedding モデル設定
CHAT_MODEL = "gpt-4o-mini"
EMBEDDING_MODEL = "text-embedding-3-small"

# tools.py から参照するエイリアス
LLM_MODEL = CHAT_MODEL

# テキスト分割設定
CHUNK_SIZE = 800
CHUNK_OVERLAP = 120

# 検索設定
TOP_K = 4

# System プロンプト（年末調整の手引き専用）
SYSTEM_PROMPT_QA = """あなたは日本の税務に詳しいアシスタントです。
ただし、回答の根拠は必ず『令和7年分 給与所得者の年末調整のしかた（年末調整の手引き）』
に基づいてください。

- 手引きに書いていないことは推測せず、「手引きに記載がないため、このアプリでは回答できません」と答えてください。
- 法令の一般論ではなく、あくまで「年末調整の実務（会社が行う手続き）」の範囲で説明してください。
- 必要に応じて、扶養控除・配偶者控除・保険料控除・住宅関連・年末調整の対象となる人/ならない人 などの論点を整理して説明してください。
- 回答の最後に、参照したページ番号を日本語でまとめてください（例：「参考：年末調整の手引き P.25〜27」）。

なお、このアプリは個別の税務判断や申告書の最終確認を代行するものではありません。
実際の申告・届出にあたっては、必ず最新の手引き・法令・税務署等の案内を確認してください。"""

from langchain_core.prompts import ChatPromptTemplate

PROMPT_TEMPLATE = ChatPromptTemplate.from_messages([
    ("system",
     "あなたは年末調整の専門家です。context（参照資料）に書かれている内容だけを使い、法令に基づいて正確に簡潔に回答してください。"),
    ("human",
     "質問: {question}\n\n---\n参考資料:\n{context}")
])