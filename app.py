# app.py
import streamlit as st
import datetime
import json  # Lottieファイル（JSON）読み込み用にインポート
from streamlit_lottie import st_lottie  # Lottie表示用ライブラリ
from models import StudentProfile, MojimojiStatus, HierarchicalMemoryStore
from services import GeminiManager

def load_lottie_file(filepath: str):
    """ローカルのLottie（JSON）ファイルを読み込む関数"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Lottieファイルの読み込みに失敗しました: {e}")
        return None

def render_line_message(role: str, content: str, student_name: str, level: int):
    """💡 メッセージをLINE風の吹き出しHTMLとしてレンダリングする関数"""
    # 改行コードをHTMLの改行タグに変換
    content_html = content.replace("\n", "<br>")
    
    if role == "user":
        # 👤 ユーザー側：右寄せ・黄緑色の吹き出し
        html = f"""
        <div style="display: flex; justify-content: flex-end; margin-bottom: 15px; width: 100%;">
            <div style="display: flex; flex-direction: column; align-items: flex-end; max-width: 75%;">
                <div style="font-size: 11px; color: #888888; margin-bottom: 3px; margin-right: 5px;">{student_name}</div>
                <div style="background-color: #9EEA6A; color: #000000; padding: 10px 14px; border-radius: 15px; border-top-right-radius: 2px; font-size: 14px; line-height: 1.4; word-break: break-all; box-shadow: 0px 1px 2px rgba(0,0,0,0.15);">
                    {content_html}
                </div>
            </div>
        </div>
        """
        st.markdown(html, unsafe_allow_html=True)
    else:
        # 🐾 MoJiMoJi側：左寄せ・白い吹き出し（レベルに応じてアイコンを卵か肉球に変化）
        avatar_emoji = "🥚" if level <= 5 else "🐦"
        html = f"""
        <div style="display: flex; justify-content: flex-start; margin-bottom: 15px; width: 100%;">
            <div style="font-size: 24px; margin-right: 10px; margin-top: 5px; background-color: #E2E8F0; width: 40px; height: 40px; border-radius: 50%; display: flex; align-items: center; justify-content: center; box-shadow: 0px 1px 2px rgba(0,0,0,0.1);">
                {avatar_emoji}
            </div>
            <div style="display: flex; flex-direction: column; align-items: flex-start; max-width: 75%;">
                <div style="font-size: 11px; color: #888888; margin-bottom: 3px; margin-left: 5px;">MoJiMoJi (Lv.{level})</div>
                <div style="background-color: #FFFFFF; color: #000000; padding: 10px 14px; border-radius: 15px; border-top-left-radius: 2px; font-size: 14px; line-height: 1.4; word-break: break-all; box-shadow: 0px 1px 2px rgba(0,0,0,0.15);">
                    {content_html}
                </div>
            </div>
        </div>
        """
        st.markdown(html, unsafe_allow_html=True)


def main():
    st.title("📖 MoJiMoJiの階層記憶育成ノート")
    st.write("今日あったこと、楽しかったこと、誰とどこにいったかを書いてみてね。")

    # ====================================================================
    # 1. セッション状態（各オブジェクト）の初期化
    # ====================================================================
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "student" not in st.session_state:
        st.session_state.student = StudentProfile()
    if "status" not in st.session_state:
        st.session_state.status = MojimojiStatus()
    if "memory" not in st.session_state:
        st.session_state.memory = HierarchicalMemoryStore()
    if "ai_manager" not in st.session_state:
        st.session_state.ai_manager = GeminiManager()

    # ショートカット変数
    student = st.session_state.student
    status = st.session_state.status
    memory = st.session_state.memory
    ai_manager = st.session_state.ai_manager

    # Lottieアニメーションの読み込み
    if status.level <= 5:
        lottie_mojimoji = load_lottie_file("resource/egg.json")
    elif status.level >= 10:
        lottie_mojimoji = load_lottie_file("resource/mojimoji.json")
    else:
        lottie_mojimoji = load_lottie_file("resource/egg.json")

    # ====================================================================
    # 2. 日付変更チェック処理
    # ====================================================================
    ai_manager.check_and_handle_date_change(memory)

    # ====================================================================
    # 3. サイドバーUIの描画
    # ====================================================================
    st.sidebar.title("👤 生徒プロフィール設定")
    student.name = st.sidebar.text_input("生徒の名前", value=student.name)
    student.grade = st.sidebar.selectbox("学年", ["小学1年生", "小学4年生", "小学6年生", "中学2年生", "高校2年生", "大学生"], index=1)
    student.gender = st.sidebar.selectbox("性別", ["男の子", "女の子", "other"], index=1)
    
    st.sidebar.markdown("---")
    
    # キャラクター（卵 or MoJiMoJi）をサイドバーに常駐表示
    if lottie_mojimoji:
        with st.sidebar:
            st_lottie(lottie_mojimoji, speed=1.0, reverse=False, loop=True, quality="high", height=150, key="sidebar_mojimoji")

    st.sidebar.title(f"🐾 MoJiMoJi (Lv. {status.level})")
    
    # 段階型リニア経験値バー
    next_exp = status.get_next_level_exp()
    st.sidebar.write(f"**Next Lv**: {status.current_exp} / {next_exp} EXP")
    st.sidebar.progress(min(status.current_exp / next_exp, 1.0))
    
    # デバッグ・デモ用の操作シミュレーターエリア
    st.sidebar.markdown("---")
    st.sidebar.subheader("⏰ デモ用：シミュレーター")
    
    # ① 日付進行ボタン
    if st.sidebar.button("📅 明日に日付を進めて要約を実行"):
        tomorrow = (datetime.datetime.strptime(memory.last_activity_date, "%Y-%m-%d") + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        ai_manager.check_and_handle_date_change(memory, simulated_date=tomorrow)
        st.success(f"日付を {tomorrow} に進め、古い記憶を圧縮ロールアップしました！")
        st.rerun()
        
    # ② レベル強制アップボタン
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("✨ Lvを1上げる"):
            status.level += 1
            st.toast(f"🛠️ レベルを **{status.level}** にしたよ！", icon="🚀")
            st.rerun()
    with col2:
        if st.button("🔮 一気にLv10へ"):
            status.level = 10
            st.toast("🛠️ レベル **10** に進化させたよ！", icon="✨")
            st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.subheader("📊 カテゴリ別内訳")
    for k, v in status.status_categories.items():
        st.sidebar.write(f"{k}: {v} EXP")
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("🧠 記憶ストア（3階層）")
    
    with st.sidebar.expander("① 今日の短期記憶（構造化）", expanded=True):
        if not memory.short_term_memories:
            st.caption("まだ今日の出来事はありません。")
        for m in memory.short_term_memories:
            st.caption(f"🕒 {m['when']}  📍 {m['where']}  👥 {m['who']}")
            st.markdown(f"**{m['what']}**")
            
    with st.sidebar.expander("② 中期記憶（過去1週間の日記ログ）", expanded=False):
        if not memory.mid_term_logs:
            st.caption("ログはありません。")
        for log in reversed(memory.mid_term_logs):
            st.info(log)
            
    with st.sidebar.expander("③ 長期記憶（数週間〜の全体要約）", expanded=False):
        if not memory.long_term_summary:
            st.caption("アーカイブはまだ空です。")
        else:
            st.warning(memory.long_term_summary)

    # ====================================================================
    # 4. メインチャットループ（💡 ここを完全にLINE風HTML表示に刷新）
    # ====================================================================
    # 過去の会話履歴をすべてLINE風に描画
    for message in st.session_state.messages:
        render_line_message(message["role"], message["content"], student.name, status.level)

    # ユーザー入力処理
    if prompt := st.chat_input("ここにメッセージを入力..."):
        # ① ユーザーの入力をその場で即座に右側の緑吹き出しとして描画
        render_line_message("user", prompt, student.name, status.level)
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # 発言の裏側分析（経験値加算）
        ai_manager.analyze_and_extract(prompt, status, memory)
        
        # ② 応答生成中アニメーション
        with st.chat_message("assistant"):  # スピナーとLottie用の一時枠
            with st.spinner("MoJiMoJiが考えています..."):
                if lottie_mojimoji:
                    st_lottie(lottie_mojimoji, height=100, loop=True, key="thinking_mojimoji")
                
                response_text = ai_manager.generate_response(prompt, student, status, memory)
                
        # ③ 完成したAIの返答をLINE風にセッションへ追加してリライト
        st.session_state.messages.append({"role": "assistant", "content": response_text})
        st.rerun()

if __name__ == "__main__":
    main()