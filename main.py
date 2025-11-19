"""年末調整R7 Q&Aアシスタント（RAG）"""

import streamlit as st
import constants as ct
from initialize import setup_retriever
from tools import ask_nentsu_qa


# -----------------------------
# 生命保険料控除（新契約）の簡易計算ロジック
# -----------------------------
def calc_new_contract_deduction(premium: float) -> int:
    """新契約（平成24年1月1日以後）の生命保険料控除額を計算する（1区分分）。

    国税庁の「新生命保険料控除」の計算式に基づき、次の階段構造で算出する：
      〜20,000円      … 支払保険料の全額
      20,001〜40,000 … 支払保険料×1/2＋10,000
      40,001〜80,000 … 支払保険料×1/4＋20,000
      80,001円〜     … 一律40,000円（上限）
    """
    if premium <= 0:
        return 0
    if premium <= 20_000:
        return int(premium)
    elif premium <= 40_000:
        return int(premium * 0.5 + 10_000)
    elif premium <= 80_000:
        return int(premium * 0.25 + 20_000)
    else:
        return 40_000  # 区分ごとの上限


# -----------------------------
# 生命保険料控除（旧契約）の簡易計算ロジック
# -----------------------------
def calc_old_contract_deduction(premium: float) -> int:
    """旧契約（平成23年12月31日以前）の生命保険料控除額を計算する（一般・個人年金 共通・所得税）。

    年間の支払保険料等に応じて、旧制度の計算式で控除額を求める：
      〜25,000円            … 支払保険料等の全額
      25,001〜50,000円      … 支払保険料等×1/2＋12,500
      50,001〜100,000円     … 支払保険料等×1/4＋25,000
      100,001円〜           … 一律50,000円（上限）
    """
    if premium <= 0:
        return 0
    if premium <= 25_000:
        return int(premium)
    elif premium <= 50_000:
        return int(premium * 0.5 + 12_500)
    elif premium <= 100_000:
        return int(premium * 0.25 + 25_000)
    else:
        return 50_000  # 旧制度1区分の上限


# -----------------------------
# 地震保険料控除（所得税）の簡易計算ロジック
# -----------------------------
def calc_earthquake_insurance_deduction(premium: float) -> int:
    """地震保険料控除（所得税）のうち、地震保険料部分の控除額を計算する。

    ・支払保険料が 50,000円 以下  … 支払保険料の全額
    ・支払保険料が 50,000円 超    … 一律 50,000円
    """
    if premium <= 0:
        return 0
    return int(min(premium, 50_000))


def calc_old_long_term_deduction(premium: float) -> int:
    """地震保険料控除（所得税）のうち、旧長期損害保険料部分の控除額を計算する。

    ・〜10,000円                … 支払保険料の全額
    ・10,001〜20,000円          … 支払保険料×1/2＋5,000
    ・20,001円〜                … 一律 15,000円
    """
    if premium <= 0:
        return 0
    if premium <= 10_000:
        return int(premium)
    elif premium <= 20_000:
        return int(premium * 0.5 + 5_000)
    else:
        return 15_000


# -----------------------------
# 共通：セッション状態初期化
# -----------------------------
def init_session_state():
    if "messages" not in st.session_state:
        st.session_state["messages"] = []


# -----------------------------
# サイドバー描画
# -----------------------------
def render_sidebar() -> str:
    """左側（サイドバー）のUIを描画して、利用目的を返す。"""
    with st.sidebar:
        # 利用目的
        st.subheader("利用目的")

        purpose = st.radio(
            "利用したい機能を選択してください",
            ("令和7年度年末調整", "令和7年度確定申告"),
            index=0,  # デフォルトは「年末調整」
        )
        
        # 🔹 チャット履歴クリア（説明なし）
        if st.button("🗑 チャット履歴をクリア"):
            st.session_state["messages"] = []

        st.markdown("---")

        # 生命保険料控除の簡易試算ツール（新／新旧）
        st.subheader("生命保険料控除のかんたん試算（所得税）")

        mode = st.radio(
            "計算したい内容を選択してください",
            (
                "新契約のみ（現行制度）",
                "新旧制度を合算（簡易計算）",
            ),
            index=0,
        )

        # -------------------------
        # ① 新契約のみ（現行制度）
        # -------------------------
        if mode == "新契約のみ（現行制度）":
            st.caption(
                "※平成24年1月1日以後に締結した保険契約（新契約）のみを対象とした簡易計算です。"
            )

            with st.expander(
                "控除証明書の金額を入力してください（新契約分）", expanded=False
            ):
                # 一般生命保険料の計算（A）
                st.markdown("**【一般生命保険料の計算】**")
                gen_new = st.number_input(
                    "A：新契約分の一般生命保険料の支払保険料合計額（年額・円）",
                    min_value=0,
                    max_value=2_000_000,
                    value=0,
                    step=10_000,
                    help="一般の生命保険（終身・定期など）のうち、新契約分の年額を入力してください。",
                    key="gen_new_only",
                )

                st.markdown("---")

                # 介護医療保険料の計算（C）
                st.markdown("**【介護医療保険料の計算】**")
                med_new = st.number_input(
                    "C：介護医療保険料の支払保険料合計額（年額・円）",
                    min_value=0,
                    max_value=2_000_000,
                    value=0,
                    step=10_000,
                    help="介護医療保険料控除の対象となる契約の年額を入力してください。",
                    key="med_new_only",
                )

                st.markdown("---")

                # 個人年金保険料の計算（D）
                st.markdown("**【個人年金保険料の計算】**")
                ann_new = st.number_input(
                    "D：新契約分の個人年金保険料の支払保険料合計額（年額・円）",
                    min_value=0,
                    max_value=2_000_000,
                    value=0,
                    step=10_000,
                    help="個人年金保険料控除の対象となる『新契約分』の年額を入力してください。",
                    key="ann_new_only",
                )

            # 各区分の控除額を計算（新契約のみ）
            gen_ded = calc_new_contract_deduction(gen_new)
            med_ded = calc_new_contract_deduction(med_new)
            ann_ded = calc_new_contract_deduction(ann_new)

            total_ded = gen_ded + med_ded + ann_ded
            # 生命保険料控除全体の上限は 120,000 円（所得税）
            total_ded_capped = min(total_ded, 120_000)

            st.markdown("**試算結果（新契約のみ・所得税の生命保険料控除）**")
            st.markdown(
                f"""
- 一般生命保険料控除：**{gen_ded:,}円**
- 介護医療保険料控除：**{med_ded:,}円**
- 個人年金保険料控除：**{ann_ded:,}円**
"""
            )

            if total_ded <= 120_000:
                st.markdown(
                    f"- 合計控除額（A＋C＋D 分）：**{total_ded_capped:,}円**"
                )
            else:
                st.markdown(
                    f"- 合計控除額（A＋C＋D 分）：**{total_ded_capped:,}円**  "
                    f"（計算上は {total_ded:,}円 ですが、上限12万円が適用されます）"
                )

            st.caption(
                "※旧契約との組合せや、実際の申告書への記入方法は、"
                "必ず『年末調整の手引き』や税務署等の案内で確認してください。"
            )

        # -------------------------
        # ② 新旧制度を合算（簡易計算）
        # -------------------------
        else:
            st.caption(
                "※新制度（新契約）と旧制度（旧契約）の両方の金額を入力して、"
                "所得税の生命保険料控除額を簡易的に試算します。"
                "旧契約のみの場合など、実際の金額と異なることがあります。"
            )

            with st.expander(
                "控除証明書の金額を入力してください（新契約＋旧契約）", expanded=False
            ):
                # 一般生命保険料（新・旧）
                st.markdown("**【一般生命保険料】**")
                col1, col2 = st.columns(2)
                with col1:
                    gen_new_combo = st.number_input(
                        "A（新）：新契約分の一般生命保険料（年額・円）",
                        min_value=0,
                        max_value=2_000_000,
                        value=0,
                        step=10_000,
                        key="gen_new_combo",
                    )
                with col2:
                    gen_old_combo = st.number_input(
                        "A（旧）：旧契約分の一般生命保険料（年額・円）",
                        min_value=0,
                        max_value=2_000_000,
                        value=0,
                        step=10_000,
                        key="gen_old_combo",
                    )

                st.markdown("---")

                # 介護医療保険料（新のみ）
                st.markdown("**【介護医療保険料】**（新制度のみ）")
                med_new_combo = st.number_input(
                    "C：介護医療保険料の支払保険料合計額（年額・円）",
                    min_value=0,
                    max_value=2_000_000,
                    value=0,
                    step=10_000,
                    key="med_new_combo",
                )

                st.markdown("---")

                # 個人年金保険料（新・旧）
                st.markdown("**【個人年金保険料】**")
                col3, col4 = st.columns(2)
                with col3:
                    ann_new_combo = st.number_input(
                        "D（新）：新契約分の個人年金保険料（年額・円）",
                        min_value=0,
                        max_value=2_000_000,
                        value=0,
                        step=10_000,
                        key="ann_new_combo",
                    )
                with col4:
                    ann_old_combo = st.number_input(
                        "D（旧）：旧契約分の個人年金保険料（年額・円）",
                        min_value=0,
                        max_value=2_000_000,
                        value=0,
                        step=10_000,
                        key="ann_old_combo",
                    )

            # 新制度分の控除額
            gen_new_ded2 = calc_new_contract_deduction(gen_new_combo)
            med_new_ded2 = calc_new_contract_deduction(med_new_combo)
            ann_new_ded2 = calc_new_contract_deduction(ann_new_combo)

            # 旧制度分の控除額（一般・個人年金）
            gen_old_ded2 = calc_old_contract_deduction(gen_old_combo)
            ann_old_ded2 = calc_old_contract_deduction(ann_old_combo)

            # 一般・個人年金は「新＋旧」を合算し、各区分の上限は 40,000 円（所得税）とする簡易計算
            gen_total_ded2 = min(gen_new_ded2 + gen_old_ded2, 40_000)
            ann_total_ded2 = min(ann_new_ded2 + ann_old_ded2, 40_000)

            # 介護医療保険料は新制度分のみ（上限 40,000 円）
            med_total_ded2 = min(med_new_ded2, 40_000)

            total_ded2 = gen_total_ded2 + med_total_ded2 + ann_total_ded2
            total_ded2_capped = min(total_ded2, 120_000)  # 全体の上限 120,000 円

            st.markdown("**試算結果（新旧制度を合算・所得税の生命保険料控除）**")
            st.markdown(
                f"""
- 一般生命保険料控除（新）：**{gen_new_ded2:,}円**
- 一般生命保険料控除（旧）：**{gen_old_ded2:,}円**
- ⇒ 一般生命保険料控除 合計（上限4万円適用後）：**{gen_total_ded2:,}円**

- 介護医療保険料控除（新のみ）：**{med_total_ded2:,}円**

- 個人年金保険料控除（新）：**{ann_new_ded2:,}円**
- 個人年金保険料控除（旧）：**{ann_old_ded2:,}円**
- ⇒ 個人年金保険料控除 合計（上限4万円適用後）：**{ann_total_ded2:,}円**
"""
            )

            if total_ded2 <= 120_000:
                st.markdown(
                    f"- 生命保険料控除の合計額：**{total_ded2_capped:,}円**"
                )
            else:
                st.markdown(
                    f"- 生命保険料控除の合計額：**{total_ded2_capped:,}円**  "
                    f"（計算上は {total_ded2:,}円 ですが、上限12万円が適用されます）"
                )

            st.caption(
                "※新旧の組合せや旧契約のみの場合の厳密な金額とは異なる場合があります。"
                "最終的な金額は、必ず『年末調整の手引き』や保険会社のシミュレーション等で確認してください。"
            )

        st.markdown("---")

        # 地震保険料控除の簡易試算ツール（所得税のみ）
        st.subheader("地震保険料控除のかんたん試算（所得税）")
        st.caption(
            "※地震保険料控除（所得税）について、年額の支払保険料から概算の控除額を試算します。"
        )

        with st.expander("地震保険料・旧長期損害保険料の金額を入力してください", expanded=False):
            eq_premium = st.number_input(
                "地震保険料の支払保険料合計額（年額・円）",
                min_value=0,
                max_value=2_000_000,
                value=0,
                step=10_000,
                help="地震保険契約に係る年間の支払保険料の合計額を入力してください。",
            )

            old_premium = st.number_input(
                "旧長期損害保険料の支払保険料合計額（年額・円）",
                min_value=0,
                max_value=2_000_000,
                value=0,
                step=10_000,
                help="平成18年12月31日以前に締結された長期損害保険契約に係る保険料などが該当します。",
            )

        eq_ded = calc_earthquake_insurance_deduction(eq_premium)
        old_ded = calc_old_long_term_deduction(old_premium)
        total_eq = eq_ded + old_ded
        total_eq_capped = min(total_eq, 50_000)  # 地震保険料控除の上限（所得税）

        st.markdown("**試算結果（所得税の地震保険料控除）**")
        st.markdown(
            f"""
- 地震保険料部分の控除額：**{eq_ded:,}円**
- 旧長期損害保険料部分の控除額：**{old_ded:,}円**
"""
        )

        if total_eq <= 50_000:
            st.markdown(f"- 合計控除額：**{total_eq_capped:,}円**")
        else:
            st.markdown(
                f"- 合計控除額：**{total_eq_capped:,}円**  "
                f"（計算上は {total_eq:,}円 ですが、上限5万円が適用されます）"
            )

        st.caption(
            "※実際の適用要件や具体的な記載方法は、必ず『年末調整の手引き』や税務署等の案内で確認してください。"
        )

        st.markdown("---")

        # よくある質問
        st.subheader("よくある質問")
        st.markdown(
            "- 扶養控除の対象になるのは誰ですか？\n"
            "- 年末調整が不要になるケースを知りたい。\n"
            "- 住宅ローン控除の書類について教えてください。"
        )

        st.markdown("---")

    return purpose

# -----------------------------
# メインエリア描画
# -----------------------------
def render_header():
    st.title(ct.APP_TITLE)
    st.caption(
        "令和7年分『給与所得者の年末調整のしかた』および関連資料をもとにしたQ&Aボットです。"
    )
    with st.expander("このアプリについて", expanded=False):
        st.markdown(
            """- 回答は **令和7年分 年末調整の手引き** や関連する税制改正資料をもとに行います。
            - 実際の申告・届出にあたっては、必ず原本の手引きや税務署等の案内をご確認ください。
            - 個別具体的な税務判断の最終決定には利用できません。"""
        )


def render_chat_history():
    for msg in st.session_state["messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])


# -----------------------------
# エントリポイント
# -----------------------------
def main():
    st.set_page_config(page_title=ct.APP_TITLE, page_icon="🧾")

    init_session_state()

    # 左側の「利用目的」＆ 各種簡易計算ツール ＆「よくある質問」
    purpose = render_sidebar()

    # ヘッダー
    render_header()

    # 令和7年度確定申告はまだ未実装 → 工事中メッセージを出して終了
    if purpose == "令和7年度確定申告":
        st.info(
            "「令和7年度確定申告」モードは現在、鋭意開発中です（工事中...）。\n"
            "今のところは「令和7年度年末調整」を選択してご利用ください。"
        )
        return  # RAG 初期化やチャットは行わない

    # ここから下は「令和7年度年末調整」モード専用の処理
    try:
        with st.spinner(
            "年末調整の手引きや関連資料を読み込み中...（初回のみ少し時間がかかります）"
        ):
            setup_retriever()
    except Exception as e:
        st.error(f"初期化中にエラーが発生しました: {e}")
        return

    render_chat_history()

    user_input = st.chat_input("年末調整について知りたいことを入力してください")
    if not user_input:
        return

    # ユーザー発話をログに追加
    st.session_state["messages"].append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # RAG による回答
    with st.chat_message("assistant"):
        with st.spinner("手引きや関連資料を確認しています..."):
            try:
                result = ask_nentsu_qa(user_input)
                answer = result["answer"]
            except Exception as e:
                answer = f"エラーが発生しました: {e}"
            st.markdown(answer)
            st.session_state["messages"].append(
                {"role": "assistant", "content": answer}
            )


if __name__ == "__main__":
    main()
