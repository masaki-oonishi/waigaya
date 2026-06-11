# app.py
import streamlit as st
import datetime
import json
import urllib.parse  
from streamlit_lottie import st_lottie
from models import StudentProfile, MojimojiStatus, HierarchicalMemoryStore
from services import GeminiManager, ACHIEVEMENT_MASTER
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
    """指定されたメダル画像を読み込み、HTMLに直埋めできるbase64文字列に変換する"""
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
    <style>html, body {{ margin: 0; padding: 0; overflow: hidden; background: transparent; height: 100%; }}</style>
    <div style="position: relative; width: 100%; height: {height}px; display: flex; justify-content: center; align-items: center; overflow: hidden; background: transparent;">
        <div id="lottie-char-{key}" style="position: absolute; width: 100%; height: 100%; z-index: 1;"></div>
        <div id="lottie-effect-{key}" style="position: absolute; width: 100%; height: 100%; z-index: 2; pointer-events: none;"></div>
    </div>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/lottie-web/5.12.2/lottie.min.js"></script>
    <script>
        lottie.loadAnimation({{ container: document.getElementById('lottie-char-{key}'), renderer: 'svg', loop: true, autoplay: true, animationData: {char_json_str} }});
        var effectData = {effect_json_str};
        if (effectData) {{ lottie.loadAnimation({{ container: document.getElementById('lottie-effect-{key}'), renderer: 'svg', loop: false, autoplay: true, animationData: effectData }}); }}
    </script>
    """
    data_url = f"data:text/html;charset=utf-8,{urllib.parse.quote(html_code)}"
    st.iframe(src=data_url, height=height)

def render_line_message(role: str, content: str, student_name: str, level: int):
    """メッセージをLINE公式そっくりの吹き出しHTMLにレンダリングする関数"""
    content_html = content.replace("\n", "<br>")
    if role == "user":
        html = f"""
        <div style="display: flex; justify-content: flex-end; margin-bottom: 15px; width: 100%;">
            <div style="display: flex; flex-direction: column; align-items: flex-end; max-width: 75%;">
                <div style="font-size: 10px; color: #888888; margin-bottom: 2px; margin-right: 5px;">{student_name}</div>
                <div style="background-color: #9EEA6A; color: #000000; padding: 8px 12px; border-radius: 12px; border-top-right-radius: 2px; font-size: 14px; box-shadow: 0px 1px 2px rgba(0,0,0,0.15);">{content_html}</div>
            </div>
        </div>
        """
    else:
        img_base64 = get_image_as_base64("resource/egg.png")
        if img_base64:
            avatar_content = f'<img src="data:image/png;base64,{img_base64}" style="width:100%; height:100%; border-radius:50%; object-fit:cover;">'
        else:
            avatar_content = "🥚"
        html = f"""
        <div style="display: flex; justify-content: flex-start; margin-bottom: 15px; width: 100%;">
            <div style="background: transparent; width:35px; height:35px; border-radius:50%; margin-right: 8px; margin-top: 5px; overflow:hidden; display:flex; align-items:center; justify-content:center;">{avatar_content}</div>
            <div style="display: flex; flex-direction: column; align-items: flex-start; max-width: 75%;">
                <div style="font-size: 10px; color: #888888; margin-bottom: 2px; margin-left: 5px;">MoJiMoJi (Lv.{level})</div>
                <div style="background-color: #FFFFFF; padding: 8px 12px; border-radius: 12px; border-top-left-radius: 2px; font-size: 14px; box-shadow: 0px 1px 2px rgba(0,0,0,0.15); color: #000000;">{content_html}</div>
            </div>
        </div>
        """
    st.markdown(html, unsafe_allow_html=True)

def show_achievement_toast(titles: list):
    """画面右上から左へスライドインして飛び出す実績解除トースト通知"""
    if not titles:
        return
    for i, title in enumerate(titles):
        medal_color = "cupper" 
        for ach_id, master in ACHIEVEMENT_MASTER.items():
            if master["title"] == title:
                medal_color = master["medal_color"]
                break
                
        img_path = f"resource/{medal_color}.png"
        img_base64 = get_image_as_base64(img_path)
        
        if img_base64:
            icon_html = f'<img src="data:image/png;base64,{img_base64}" style="width: 45px; height: 45px; object-fit: contain;">'
        else:
            icon_html = '<div style="font-size: 24px;">🏆</div>' 

        toast_html = f"""
        <div id="ach-toast-{i}" style="
            position: fixed; top: {70 + (i * 80)}px; right: 20px; width: 290px; 
            background: linear-gradient(135deg, #FFF7E6 0%, #FFF 100%);
            border-left: 6px solid #FFD700; border-radius: 8px; padding: 12px;
            box-shadow: 0px 4px 15px rgba(0,0,0,0.2); z-index: 99999;
            display: flex; align-items: center; gap: 12px; color: #333;
            animation: slideInRight 0.5s ease-out forwards, fadeOut 0.5s ease-in 4.5s forwards;
        ">
            <div style="flex-shrink: 0; display: flex; align-items: center; justify-content: center; width: 45px;">
                {icon_html}
            </div>
            <div>
                <div style="font-size: 11px; color: #FF8C00; font-weight: bold; margin-bottom: 2px;">★ 隠れ実績を解除したもじ！</div>
                <div style="font-size: 13px; font-weight: bold;">{title}</div>
            </div>
        </div>
        <style>
        @keyframes slideInRight {{ 0% {{ transform: translateX(350px); opacity: 0; }} 100% {{ transform: translateX(0); opacity: 1; }} }}
        @keyframes fadeOut {{ 0% {{ opacity: 1; }} 100% {{ opacity: 0; transform: translateY(-20px); }} }}
        </style>
        """
        st.markdown(toast_html, unsafe_allow_html=True)


def main():
    if "messages" not in st.session_state: st.session_state.messages = []
    if "student" not in st.session_state: st.session_state.student = StudentProfile()
    if "status" not in st.session_state: st.session_state.status = MojimojiStatus()
    if "memory" not in st.session_state: st.session_state.memory = HierarchicalMemoryStore()
    if "ai_manager" not in st.session_state: st.session_state.ai_manager = GeminiManager()
    if "screen" not in st.session_state: st.session_state.screen = "room"
    if "show_lvup_effect" not in st.session_state: st.session_state.show_lvup_effect = False 
    if "toast_queue" not in st.session_state: st.session_state.toast_queue = []

    student = st.session_state.student
    status = st.session_state.status
    memory = st.session_state.memory
    ai_manager = st.session_state.ai_manager

    if st.session_state.toast_queue:
        show_achievement_toast(st.session_state.toast_queue)
        st.session_state.toast_queue = [] 

    l_egg = load_lottie_file("resource/egg.json")
    l_moji = load_lottie_file("resource/mojimoji.json")
    l_letter = load_lottie_file("resource/letter.json")
    l_lvup = load_lottie_file("resource/level_up.json")

    current_lottie = l_egg if status.level <= 5 else l_moji
    ai_manager.check_and_handle_date_change(memory)
    active_effect = l_lvup if st.session_state.show_lvup_effect else None

    # ====================================================================
    # ⚙️ サイドバーUI
    # ====================================================================
    with st.sidebar:
        st.title("👤 プロフィール")
        student.name = st.text_input("生徒の名前", value=student.name)
        student.grade = st.selectbox("学年", ["小学1年生", "小学4年生", "小学6年生", "中学2年生", "高校2年生", "大学生"], index=1)
        student.gender = st.radio("性別", ["女の子", "男の子"], index=0)
        
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

        st.markdown("---")
        st.subheader("📊 分類ダッシュボード")
        chart_data = {"カテゴリ": list(status.status_categories.keys()), "獲得した累計EXP": list(status.status_categories.values())}
        st.bar_chart(chart_data, x="カテゴリ", y="獲得した累計EXP", color="#9EEA6A")
        
        st.markdown("**📜 過去の分類・分析履歴**")
        if not memory.classification_history:
            st.caption("履歴はまだありません。")
        for log in reversed(memory.classification_history):
            st.markdown(f"<div style='font-size: 11px; color:#555;'>📅 {log['date']} | {log['type']}</div>", unsafe_allow_html=True)
            st.markdown(f"<div style='font-size: 12px; font-weight:bold; margin-bottom:4px;'>『 {log['text']} 』</div>", unsafe_allow_html=True)
            
            if log.get("is_rejected"):
                st.markdown(
                    "<div style='background-color: #FFF0F0; padding: 6px 10px; border-left: 3px solid #FF4B4B; border-radius: 4px; margin: 4px 0; font-size: 11px;'>"
                    "<span style='color: #CC0000; font-weight: bold;'>🚨 フィルター発動:</span> 0 EXP (一括無効化)"
                    "</div>", 
                    unsafe_allow_html=True
                )
            elif log["gained"]:
                for g in log["gained"]:
                    pts = f"+{g['points']}" if g['points'] > 0 else "+0"
                    st.markdown(f"<div style='font-size: 11px; margin-left: 4px;'>- {g['category']}: <b>{pts} EXP</b><br><span style='color:#666; font-style:italic;'>➔ 「{g['reason']}」</span></div>", unsafe_allow_html=True)
            
            mem_text = log.get("extracted_memory", "なし")
            if mem_text == "（保存なし）": mem_text = "(不適切判定のため保存なし)"
            st.markdown(f"<div style='font-size: 11px; margin-left: 4px; margin-top:2px;'>🧠 <b>短期記憶:</b> <span style='color: #00A86B; font-weight: bold;'>{mem_text}</span></div>", unsafe_allow_html=True)
            st.markdown("<hr style='margin-top: 8px; margin-bottom: 8px; border-color: #EEEEEE;'>", unsafe_allow_html=True)

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
            st.markdown(f"<div style='text-align: center; font-size: 11px; color: #666; margin-top: 5px;'>EXP: {status.current_exp} / {next_exp}</div>", unsafe_allow_html=True)
            
        st.markdown("<div style='margin-bottom: 25px;'></div>", unsafe_allow_html=True)
        st.markdown("<h3 style='text-align: center;'>今日なにする？</h3>", unsafe_allow_html=True)
        
        c_btn1, c_btn2, c_btn3 = st.columns(3)
        with c_btn1:
            if st.button("📖 日記ルートへ", use_container_width=True, type="primary"):
                st.session_state.screen = "diary"; st.rerun()
        with c_btn2:
            if st.button("💬 会話ルートへ", use_container_width=True, type="primary"):
                st.session_state.screen = "chat"; st.rerun()
        with c_btn3:
            if st.button("🏅 隠れ実績図鑑をみる", use_container_width=True, type="primary"):
                st.session_state.screen = "achievements"; st.rerun()

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
            st.info("ノートを大切に閉じて、また明日おもしろかったことをたくさん教えてね。")
            if st.button("🏠 部屋に戻る", use_container_width=True, type="primary"):
                st.session_state.screen = "room"; st.rerun()
        else:
            st.markdown("### ✍️ 今日の日記をノートに書こう")
            diary_input = st.text_area("今日あった嬉しかったことや、がんばったことを教えてね！", placeholder="例：あさちゃんといっしょに校庭でサッカーをしたよ！", height=120)
            
            if st.button("🚀 日記をノートに保存する", use_container_width=True):
                if diary_input.strip():
                    old_mem_count = len(memory.short_term_memories)
                    
                    # 💡 【今回の大改善】日記のデータ分析中も、会話と同じくスピナーのぐるぐるを発生させます！
                    with st.spinner("MoJiMoJiが日記を読んでいるもじ..."):
                        gained, lvup, is_rejected, fb, toasts = ai_manager.analyze_and_extract(diary_input, student, status, memory, is_diary=True)
                    
                    st.session_state.last_gained_exp = gained
                    st.session_state.diary_feedback = fb
                    st.session_state.diary_is_rejected = is_rejected
                    if toasts: st.session_state.toast_queue += toasts 
                    
                    if not is_rejected: memory.has_written_diary_today = True  
                    if lvup: st.session_state.show_lvup_effect = True 
                        
                    new_mem = memory.short_term_memories[-1]["what"] if len(memory.short_term_memories) > old_mem_count else "なし"
                    memory.classification_history.append({
                        "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "type": "📖 日記", "text": diary_input,
                        "gained": gained, "extracted_memory": new_mem if not is_rejected else "（保存なし）", "is_rejected": is_rejected
                    })
                    st.session_state.screen = "diary_animation"; st.rerun()
                    
            if st.button("🏠 部屋に戻る", use_container_width=True):
                st.session_state.screen = "room"; st.rerun()

    # 💌 【日記ルート】演出画面
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

        is_rejected = st.session_state.get("diary_is_rejected", False)
        feedback_text = st.session_state.get("diary_feedback", "")
        
        if is_rejected:
            st.error("⚠️ 今回獲得経験値: 0 EXP （不適切な言葉が含まれていたため、データは保存されませんでした）")
        else:
            total_gained = sum(g["points"] for g in st.session_state.get("last_gained_exp", []))
            st.success(f"🌟 今回獲得した全体の経験値: +{total_gained} EXP !")
            if l_letter: st.markdown("<div style='text-align:center;'>", unsafe_allow_html=True); st_lottie(l_letter, height=150, loop=False, key="letter_anim"); st.markdown("</div>", unsafe_allow_html=True)
            
        render_line_message("assistant", feedback_text, student.name, status.level)
        if st.button("🏠 部屋に戻る", use_container_width=True):
            st.session_state.screen = "room"; st.rerun()

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
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            with chat_container:
                render_line_message("user", prompt, student.name, status.level)
                
            old_mem_count = len(memory.short_term_memories)
            
            with st.spinner("MoJiMoJiが考えています..."):
                gained, lvup, is_rejected, fb, toasts = ai_manager.analyze_and_extract(prompt, student, status, memory, is_diary=False)
                if lvup: st.session_state.show_lvup_effect = True 
                if toasts: st.session_state.toast_queue += toasts 
                
                if is_rejected:
                    response_text = fb
                else:
                    response_text = ai_manager.generate_response(st.session_state.messages, student, status, memory)
            
            new_mem = memory.short_term_memories[-1]["what"] if len(memory.short_term_memories) > old_mem_count else "なし"
            memory.classification_history.append({
                "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "type": "💬 会話", "text": prompt,
                "gained": gained, "extracted_memory": new_mem if not is_rejected else "（保存なし）", "is_rejected": is_rejected
            })
            st.session_state.messages.append({"role": "assistant", "content": response_text})
            st.rerun()

    # 📊 【案内画面】
    elif st.session_state.screen == "dashboard":
        st.subheader("📊 分類ダッシュボード案内")
        st.markdown("<div style='margin-bottom: 15px;'></div>", unsafe_allow_html=True)
        st.info("💡 分類ダッシュボードとタイムラインは、←左側のサイドバーの下部に引っ越ししたもじ！")
        st.markdown("いつでもお部屋やおしゃべり画面を見ながらチェックできるようになったもじ✨")
        if st.button("🏠 お部屋に戻る", use_container_width=True, type="primary"):
            st.session_state.screen = "room"; st.rerun()

    # 🏅 【隠れ実績図鑑ルート】
    elif st.session_state.screen == "achievements":
        col_ac_title, col_ac_btn = st.columns([8, 2])
        with col_ac_title:
            st.subheader("🏅 隠れ実績図鑑（たからさがし）")
        with col_ac_btn:
            if st.button("🏠 お部屋へ", use_container_width=True, type="primary"):
                st.session_state.screen = "room"; st.rerun()
                
        st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)

        for ach_id, master in ACHIEVEMENT_MASTER.items():
            user_data = memory.user_achievements.get(ach_id, {"current_value": 0, "is_unlocked": False, "unlocked_at": None})
            is_unlocked = user_data["is_unlocked"]
            
            img_path = f"resource/{master['medal_color']}.png"
            img_base64 = get_image_as_base64(img_path)
            
            if is_unlocked:
                img_style = "width: 65px; height: 65px; object-fit: contain;"
                title_html = f"<span style='font-size:16px; font-weight:bold; color:#D4AF37;'>🏆 {master['title']}</span>"
                detail_html = f"<span style='font-size:13px; color:#333;'>条件: {master['condition']}</span>"
                status_html = f"<span style='font-size:11px; color:#228B22; font-weight:bold;'>✨達成日: {user_data['unlocked_at']}</span>"
            else:
                img_style = "width: 65px; height: 65px; object-fit: contain; filter: brightness(70%) saturate(80%); opacity: 0.5;"
                title_html = f"<span style='font-size:16px; font-weight:bold; color:#777;'>🔒 {master['title']}</span>"
                detail_html = f"<span style='font-size:13px; color:#888; font-style:italic;'>ヒント: {master['hint']}</span>"
                
                if master["display_type"] == "open":
                    status_html = f"<span style='font-size:12px; color:#666;'>進捗: {user_data['current_value']} / {master['target_value']} 回</span>"
                elif master["display_type"] == "mask":
                    status_html = f"<span style='font-size:12px; color:#666;'>進捗: 〇 / {master['target_value']} 回</span>"
                else: 
                    status_html = f"<span style='font-size:12px; color:#E67E22; font-weight:bold;'>進捗: ？？？</span>"

            img_tag = f'<img src="data:image/png;base64,{img_base64}" style="{img_style}">' if img_base64 else f"<div style='font-size:30px;'>🔒</div>"

            achievement_card_html = f"""
            <div style="display: flex; align-items: center; padding: 12px 5px; border-bottom: 1px solid #EEEEEE; width: 100%;">
                <div style="flex-shrink: 0; margin-right: 15px; display: flex; align-items: center; justify-content: center; width: 70px;">
                    {img_tag}
                </div>
                <div style="display: flex; flex-direction: column; flex-grow: 1;">
                    <div style="margin-bottom: 2px;">{title_html}</div>
                    <div style="margin-bottom: 4px;">{detail_html}</div>
                    <div>{status_html}</div>
                </div>
            </div>
            """
            st.markdown(achievement_card_html, unsafe_allow_html=True)

    if st.session_state.show_lvup_effect:
        st.session_state.show_lvup_effect = False

if __name__ == "__main__":
    main()