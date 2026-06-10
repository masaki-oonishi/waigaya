# app.py
import streamlit as st
import datetime
import json
import urllib.parse  
from streamlit_lottie import st_lottie
from models import StudentProfile, MojimojiStatus, HierarchicalMemoryStore
from services import GeminiManager
import base64
from pathlib import Path

def load_lottie_file(filepath: str):
    """ローカルのLottie（JSON）ファイルを安全に読み込む関数"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return None

def get_image_as_base64(path):
    """指定されたパスの画像を読み込み、HTMLに埋め込めるbase64文字列に変換する"""
    if Path(path).is_file():
        with open(path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    return None

def render_mojimoji_with_overlay(character_data, effect_data=None, height=200, key=""):
    """HTML5/CSS3を用いて、マスコットの真上にレベルアップエフェクトを完全に重ねて再生する関数"""
    if not character_data:
        return
        
    char_json_str = json.dumps(character_data)
    effect_json_str = json.dumps(effect_data) if effect_data else "null"

    html_code = f"""
    <style>
        html, body {{
            margin: 0;
            padding: 0;
            overflow: hidden;
            background: transparent;
            height: 100%;
            width: 100%;
        }}
    </style>
    <div style="position: relative; width: 100%; height: {height}px; display: flex; justify-content: center; align-items: center; overflow: hidden; background: transparent;">
        <div id="lottie-char-{key}" style="position: absolute; width: 100%; height: 100%; z-index: 1;"></div>
        <div id="lottie-effect-{key}" style="position: absolute; width: 100%; height: 100%; z-index: 2; pointer-events: none;"></div>
    </div>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/lottie-web/5.12.2/lottie.min.js"></script>
    <script>
        lottie.loadAnimation({{
            container: document.getElementById('lottie-char-{key}'),
            renderer: 'svg',
            loop: true,
            autoplay: true,
            animationData: {char_json_str}
        }});
        
        var effectData = {effect_json_str};
        if (effectData) {{
            lottie.loadAnimation({{
                container: document.getElementById('lottie-effect-{key}'),
                renderer: 'svg',
                loop: false,
                autoplay: true,
                animationData: effectData
            }});
        }}
    </script>
    """
    
    data_url = f"data:text/html;charset=utf-8,{urllib.parse.quote(html_code)}"
    st.iframe(src=data_url, height=height)

def render_line_message(role: str, content: str, student_name: str, level: int):
    """メッセージをLINE公式そっくりの吹き出しHTMLにレンダリングする関数"""
    content_html = content.replace("\n", "<br>")
    if role == "user":
        bg, align, radius = "#9EEA6A", "flex-end", "border-top-right-radius: 2px;"
        label = student_name
        html = f"""
        <div style="display: flex; justify-content: {align}; margin-bottom: 15px; width: 100%;">
            <div style="display: flex; flex-direction: column; align-items: {align}; max-width: 75%;">
                <div style="font-size: 10px; color: #888888; margin-bottom: 2px; margin-right: 5px;">{label}</div>
                <div style="background-color: {bg}; color: #000000; padding: 8px 12px; border-radius: 12px; {radius} font-size: 14px; box-shadow: 0px 1px 2px rgba(0,0,0,0.15);">
                    {content_html}
                </div>
            </div>
        </div>
        """
    else:
        bg, align, radius = "#FFFFFF", "flex-start", "border-top-left-radius: 2px;"
        label = f"MoJiMoJi (Lv.{level})"
        
        img_base64 = get_image_as_base64("resource/egg.png")
        
        if img_base64:
            avatar_content = f'<img src="data:image/png;base64,{img_base64}" style="width:100%; height:100%; border-radius:50%; object-fit:cover; opacity: 1 !important;">'
            avatar_style = "background: transparent; width:35px; height:35px; border-radius:50%; margin-right: 8px; margin-top: 5px; overflow:hidden;"
        else:
            avatar_emoji = "🥚" if level <= 5 else "🐾"
            avatar_content = avatar_emoji
            avatar_style = "font-size: 20px; background:#E2E8F0; width:35px; height:35px; border-radius:50%; display:flex; align-items:center; justify-content:center; margin-right: 8px; margin-top: 5px;"

        html = f"""
        <div style="display: flex; justify-content: {align}; margin-bottom: 15px; width: 100%;">
            <div style="{avatar_style}">
                {avatar_content}
            </div>
            <div style="display: flex; flex-direction: column; align-items: {align}; max-width: 75%;">
                <div style="font-size: 10px; color: #888888; margin-bottom: 2px; margin-left: 5px;">{label}</div>
                <div style="background-color: {bg}; padding: 8px 12px; border-radius: 12px; {radius} font-size: 14px; box-shadow: 0px 1px 2px rgba(0,0,0,0.15); color: #000000;">
                    {content_html}
                </div>
            </div>
        </div>
        """
    st.markdown(html, unsafe_allow_html=True)


def main():
    if "messages" not in st.session_state: st.session_state.messages = []
    if "student" not in st.session_state: st.session_state.student = StudentProfile()
    if "status" not in st.session_state: st.session_state.status = MojimojiStatus()
    if "memory" not in st.session_state: st.session_state.memory = HierarchicalMemoryStore()
    if "ai_manager" not in st.session_state: st.session_state.ai_manager = GeminiManager()
    if "screen" not in st.session_state: st.session_state.screen = "room"
    if "show_lvup_effect" not in st.session_state: st.session_state.show_lvup_effect = False 

    student = st.session_state.student
    status = st.session_state.status
    memory = st.session_state.memory
    ai_manager = st.session_state.ai_manager

    # Lottieアニメーションの読み込み
    l_egg = load_lottie_file("resource/egg.json")
    l_moji = load_lottie_file("resource/mojimoji.json")
    l_letter = load_lottie_file("resource/letter.json")
    l_lvup = load_lottie_file("resource/level_up.json")

    current_lottie = l_egg if status.level <= 5 else l_moji
    ai_manager.check_and_handle_date_change(memory)

    active_effect = l_lvup if st.session_state.show_lvup_effect else None

    # ====================================================================
    # 2. サイドバーUI（プロフィール・デバッグ）
    # ====================================================================
    with st.sidebar:
        st.title("👤 プロフィール")
        student.name = st.text_input("生徒の名前", value=student.name)
        student.grade = st.selectbox("学年", ["小学1年生", "小学4年生", "小学6年生", "中学2年生", "高校2年生", "大学生"], index=1)
        student.gender = st.radio("性別", ["女の子", "男の子"], index=0)
        
        if l_lvup is None:
            st.error("⚠️ resource/level_up.json が見つからないか破損しています！")
        
        st.markdown("---")
        st.title(f"🐾 MoJi (Lv.{status.level})")
        next_exp = status.get_next_level_exp()
        st.write(f"Next: {status.current_exp} / {next_exp} EXP")
        st.progress(min(status.current_exp / next_exp, 1.0))
        
        st.markdown("---")
        st.subheader("🎛️ デモ用シミュレーター")
        st.caption(f"活動基準日: `{memory.last_activity_date}`")
        if st.button("📅 明日へ日付を進める（制限リセット）", use_container_width=True):
            tomorrow = (datetime.datetime.strptime(memory.last_activity_date, "%Y-%m-%d") + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
            ai_manager.check_and_handle_date_change(memory, simulated_date=tomorrow)
            st.rerun()
            
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✨ Lv + 1", use_container_width=True):
                status.level += 1
                st.session_state.show_lvup_effect = True 
                st.rerun()
        with col2:
            if st.button("🔮 一気にLv10", use_container_width=True):
                status.level = 10
                st.session_state.show_lvup_effect = True 
                st.rerun()

        st.markdown("---")
        st.subheader("📊 カテゴリ別内訳")
        for k, v in status.status_categories.items():
            st.write(f"{k}: {v} EXP")
            
        st.markdown("---")
        st.subheader("🧠 3階層記憶ストア")
        with st.expander("① 今日の短期記憶", expanded=True):
            if not memory.short_term_memories: st.caption("まだありません。")
            for m in memory.short_term_memories: st.caption(f"🕒 {m.get('when','')} 📍 {m.get('where','')} 👥 {m.get('who','')}\n**{m.get('what','')}**")
        with st.expander("② 中期記憶", expanded=False):
            for log in reversed(memory.mid_term_logs): st.info(log)
        with st.expander("③ 長期記憶", expanded=False):
            if memory.long_term_summary: st.warning(memory.long_term_summary)

    # ====================================================================
    # 3. メイン画面のルート分岐
    # ====================================================================

    # 🏠 【部屋ルート】トップ画面
    if st.session_state.screen == "room":
        st.subheader(f"🏠 {student.name}ちゃんの MoJiMoJiの部屋")
        
        render_mojimoji_with_overlay(current_lottie, active_effect, height=300, key=f"room_{status.level}_{bool(active_effect)}")
        
        st.markdown(f"<h3 style='text-align: center; margin-top: 5px; margin-bottom: 5px;'>🐾 Lv.{status.level}</h3>", unsafe_allow_html=True)
        next_exp = status.get_next_level_exp()
        
        col_r_bar1, col_r_bar2, col_r_bar3 = st.columns([2, 6, 2])
        with col_r_bar2:
            st.progress(min(status.current_exp / next_exp, 1.0))
            st.markdown(f"<div style='text-align: center; font-size: 11px; color: #666;'>EXP: {status.current_exp} / {next_exp}</div>", unsafe_allow_html=True)
            
        st.markdown("<div style='margin-bottom: 25px;'></div>", unsafe_allow_html=True)
        st.markdown("<h3 style='text-align: center;'>今日なにする？</h3>", unsafe_allow_html=True)
        c_btn1, c_btn2 = st.columns(2)
        with c_btn1:
            if st.button("📖 日記ルートへ", use_container_width=True, type="primary"):
                st.session_state.screen = "diary"; st.rerun()
        with c_btn2:
            if st.button("💬 会話ルートへ", use_container_width=True, type="primary"):
                st.session_state.screen = "chat"; st.rerun()
                
        st.markdown("<div style='margin-bottom: 15px;'></div>", unsafe_allow_html=True)
        if st.button("📊 分類ダッシュボードを見る", use_container_width=True):
            st.session_state.screen = "dashboard"; st.rerun()

    # 📖 【日記ルート】入力画面
    elif st.session_state.screen == "diary":
        st.subheader("📖 記憶と日記のノート")
        st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)
        
        col_d_top1, col_d_top2, col_d_top3 = st.columns([3, 4, 3])
        with col_d_top2:
            render_mojimoji_with_overlay(current_lottie, active_effect, height=180, key=f"diary_top_{status.level}_{bool(active_effect)}")
            st.markdown(f"<h4 style='text-align: center; margin-top: 5px; margin-bottom: 5px;'>🐾 Lv.{status.level}</h4>", unsafe_allow_html=True)
            next_exp = status.get_next_level_exp()
            st.progress(min(status.current_exp / next_exp, 1.0))
            st.markdown(f"<div style='text-align: center; font-size: 11px; color: #666;'>EXP: {status.current_exp} / {next_exp}</div>", unsafe_allow_html=True)
            
        st.markdown("<hr style='margin-top: 15px; margin-bottom: 15px;'>", unsafe_allow_html=True)

        if memory.has_written_diary_today:
            st.warning(f"🌟 今日のお手紙（日記）はもう {student.name}ちゃんから預かったもじ！")
            st.info("また明日おもしろかったことをたくさん教えてね。")
            if st.button("🏠 部屋に戻る", use_container_width=True, type="primary"):
                st.session_state.screen = "room"; st.rerun()
        else:
            st.markdown("### ✍️ 今日の日記をノートに書こう")
            diary_input = st.text_area("今日あった嬉しかったことや、がんばったことを教えてね！", placeholder="例：あさちゃん。と一緒に公園でサッカーをしたよ！", height=120)
            
            if st.button("🚀 日記をノートに保存する", use_container_width=True):
                if diary_input.strip():
                    old_mem_count = len(memory.short_term_memories)
                    
                    # 💡 【改修】引数と戻り値を新フィルター仕様に完全同期
                    gained, lvup, is_rejected, feedback_text = ai_manager.analyze_and_extract(diary_input, student, status, memory, is_diary=True)
                    
                    st.session_state.last_gained_exp = gained
                    st.session_state.diary_feedback = feedback_text
                    st.session_state.diary_is_rejected = is_rejected
                    
                    # 💡 安全フィルターで拒絶されなかった場合のみ、本日の日記制限をかける
                    if not is_rejected:
                        memory.has_written_diary_today = True  
                    if lvup:
                        st.session_state.show_lvup_effect = True 
                        
                    new_mem = memory.short_term_memories[-1]["what"] if len(memory.short_term_memories) > old_mem_count else "なし"
                    memory.classification_history.append({
                        "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "type": "📖 日記",
                        "text": diary_input,
                        "gained": gained,
                        "extracted_memory": new_mem if not is_rejected else "（不適切判定のため保存なし）",
                        "is_rejected": is_rejected
                    })
                    
                    st.session_state.screen = "diary_animation"
                    st.rerun()
                    
            if st.button("🏠 部屋に戻る", use_container_width=True):
                st.session_state.screen = "room"; st.rerun()

    # 💌 【日記ルート】お手紙演出画面（💡 【大進化】獲得した全体の経験値と、MoJiMoJiのフィードバック吹き出しを完全表示！）
    elif st.session_state.screen == "diary_animation":
        st.subheader("📖 記憶と日記のノート")
        st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)
        
        col_da_top1, col_da_top2, col_da_top3 = st.columns([3, 4, 3])
        with col_da_top2:
            render_mojimoji_with_overlay(current_lottie, active_effect, height=180, key=f"diary_anim_top_{status.level}_{bool(active_effect)}")
            st.markdown(f"<h4 style='text-align: center; margin-top: 5px; margin-bottom: 5px;'>🐾 Lv.{status.level}</h4>", unsafe_allow_html=True)
            next_exp = status.get_next_level_exp()
            st.progress(min(status.current_exp / next_exp, 1.0))
            st.markdown(f"<div style='text-align: center; font-size: 11px; color: #666;'>EXP: {status.current_exp} / {next_exp}</div>", unsafe_allow_html=True)
            
        st.markdown("<hr style='margin-top: 15px; margin-bottom: 15px;'>", unsafe_allow_html=True)

        # 💡 セキュリティフィルターの判定とメッセージを取得
        is_rejected = st.session_state.get("diary_is_rejected", False)
        feedback_text = st.session_state.get("diary_feedback", "")
        
        if is_rejected:
            st.markdown("<h3 style='text-align: center; color: #FF4B4B; margin-top: 0px;'>⚠️ ノートにバツがついちゃったもじ...</h3>", unsafe_allow_html=True)
            st.error("今回の獲得経験値: 0 EXP （不適切な言葉が含まれていたため、データは保存されませんでした）")
        else:
            st.markdown("<h3 style='text-align: center; margin-top: 0px;'>💌 お手紙を預かったもじ！</h3>", unsafe_allow_html=True)
            # 💡 日記で獲得した全体の経験値（10点）を合算表示
            total_gained = sum(g["points"] for g in st.session_state.get("last_gained_exp", []))
            st.success(f"🌟 今回獲得した全体の経験値: +{total_gained} EXP !")
            
        if l_letter and not is_rejected: 
            st_lottie(l_letter, height=180, loop=False, key="letter_anim")
            
        # 💡 MoJiMoJiのフィードバック吹き出しをLINE風に配置（全無効時はここで優しく諭す）
        st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
        render_line_message("assistant", feedback_text, student.name, status.level)
            
        st.markdown("<div style='box-sizing: border-box; margin-bottom: 15px;'></div>", unsafe_allow_html=True)
        c_an1, c_an2 = st.columns(2)
        with c_an1:
            if st.button("🏠 部屋に戻る", use_container_width=True):
                if "last_gained_exp" in st.session_state: del st.session_state.last_gained_exp
                if "diary_feedback" in st.session_state: del st.session_state.diary_feedback
                if "diary_is_rejected" in st.session_state: del st.session_state.diary_is_rejected
                st.session_state.screen = "room"; st.rerun()
        with c_an2:
            btn_label = "💬 新しいお話をする" if is_rejected else "💬 このまま会話する"
            if st.button(btn_label, use_container_width=True, type="primary"):
                if "last_gained_exp" in st.session_state: del st.session_state.last_gained_exp
                if "diary_feedback" in st.session_state: del st.session_state.diary_feedback
                if "diary_is_rejected" in st.session_state: del st.session_state.diary_is_rejected
                st.session_state.screen = "chat"; st.rerun()

    # 💬 【会話ルート】LINE風トーク画面
    elif st.session_state.screen == "chat":
        col_head_title, col_head_btn = st.columns([8, 2])
        with col_head_title: st.subheader("💬 MoJiMoJiトーク")
        with col_head_btn:
            if st.button("🏠 戻る", use_container_width=True):
                st.session_state.screen = "room"; st.rerun()
                
        st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)
        
        col_chat_top1, col_chat_top2, col_chat_top3 = st.columns([3, 4, 3])
        with col_chat_top2:
            render_mojimoji_with_overlay(current_lottie, active_effect, height=180, key=f"chat_top_{status.level}_{bool(active_effect)}")
            st.markdown(f"<h4 style='text-align: center; margin-top: 5px; margin-bottom: 5px;'>🐾 Lv.{status.level}</h4>", unsafe_allow_html=True)
            next_exp = status.get_next_level_exp()
            st.progress(min(status.current_exp / next_exp, 1.0))
            st.markdown(f"<div style='text-align: center; font-size: 11px; color: #666;'>EXP: {status.current_exp} / {next_exp}</div>", unsafe_allow_html=True)
            
        st.markdown("<hr style='margin-top: 15px; margin-bottom: 15px;'>", unsafe_allow_html=True)
        
        chat_container = st.container()
        with chat_container:
            for message in st.session_state.messages:
                render_line_message(message["role"], message["content"], student.name, status.level)

        if prompt := st.chat_input("ここにメッセージを入力..."):
            render_line_message("user", prompt, student.name, status.level)
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            old_mem_count = len(memory.short_term_memories)
            
            with st.spinner("MoJiMoJiが考えています..."):
                # 💡 解析と同時に、全無効フラグとフィードバックを取得
                gained, lvup, is_rejected, feedback_text = ai_manager.analyze_and_extract(prompt, student, status, memory, is_diary=False)
                if lvup:
                    st.session_state.show_lvup_effect = True 
                
                # 💡 【会話の全無効フォロー】不適切表現を検知した場合は、二重にAPIを叩かず、諭すメッセージ（feedback）をそのまま返答として即座に採用！
                if is_rejected:
                    response_text = feedback_text
                else:
                    # 健全な会話の時は履歴を同期して返答を生成
                    response_text = ai_manager.generate_response(st.session_state.messages, student, status, memory)
            
            new_mem = memory.short_term_memories[-1]["what"] if len(memory.short_term_memories) > old_mem_count else "なし"
            memory.classification_history.append({
                "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                "type": "💬 会話",
                "text": prompt,
                "gained": gained,
                "extracted_memory": new_mem if not is_rejected else "（不適切判定のため保存なし）",
                "is_rejected": is_rejected
            })
                    
            st.session_state.messages.append({"role": "assistant", "content": response_text})
            st.rerun()

    # 📊 【ダッシュボードルート】可視化画面
    elif st.session_state.screen == "dashboard":
        col_dash_title, col_dash_btn = st.columns([8, 2])
        with col_dash_title: st.subheader("📊 分類ダッシュボード")
        with col_dash_btn:
            if st.button("🏠 戻る", use_container_width=True, type="primary"):
                st.session_state.screen = "room"; st.rerun()
                
        st.markdown("<div style='margin-bottom: 15px;'></div>", unsafe_allow_html=True)
        
        st.markdown("### 📈 カテゴリ別の成長バランス")
        chart_data = {
            "カテゴリ": list(status.status_categories.keys()),
            "獲得した累計EXP": list(status.status_categories.values())
        }
        st.bar_chart(chart_data, x="カテゴリ", y="獲得した累計EXP", color="#9EEA6A")
        
        st.markdown("<div style='margin-bottom: 30px;'></div>", unsafe_allow_html=True)
        
        st.markdown("### 📜 過去の分類・分析履歴（タイムライン）")
        if not memory.classification_history:
            st.info("まだ分析履歴がありません。")
        else:
            for log in reversed(memory.classification_history):
                st.markdown(f"**📅 {log['date']} | 種類: {log['type']}**")
                st.markdown(f"**子供の発言:** 『 {log['text']} 』")
                
                # 💡 ダッシュボードのタイムラインにも一括無効化のセキュリティセキュリティログを明記
                if log.get("is_rejected"):
                    st.markdown("🚨 **セキュリティフィルター発動:** 不適切な言葉（いじめ・暴言）を検知したため、この発言全体の経験値付与および階層記憶への書き込みを【一括無効化（0 EXP）】しました。")
                elif log["gained"]:
                    st.markdown("✨ **分類成功 (EXP獲得内訳):**")
                    for g in log["gained"]:
                        reason_str = f" ➔ 評価された表現: *「{g['reason']}」*" if g.get("reason") else ""
                        st.markdown(f"- **{g['category']}**: `+{g['points']} EXP` {reason_str}")
                else:
                    st.markdown("❌ **分類結果:** 無効・対象外（単純な相槌、挨拶、または中身のない雑談）")
                    
                st.markdown(f"🧠 **抽出された短期記憶:** `{log['extracted_memory']}`")
                st.markdown("<hr style='margin-top: 10px; margin-bottom: 15px; border-color: #eee;'>", unsafe_allow_html=True)

    if st.session_state.show_lvup_effect:
        st.session_state.show_lvup_effect = False

if __name__ == "__main__":
    main()