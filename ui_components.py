# ui_components.py
import streamlit as st
import json
import urllib.parse
import base64
from pathlib import Path
from services import ACHIEVEMENT_MASTER

def load_lottie_file(filepath: str):
    """LottieアニメーションのJSONファイルを安全に読み込む"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return None


def get_image_as_base64(path):
    """ローカル画像をHTML埋め込み用のBase64文字列に変換する"""
    if Path(path).is_file():
        with open(path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    return None


def render_mojimoji_with_overlay(character_data, effect_data=None, height=200, key=""):
    """MoJiMoJiのグラフィック（Lottie or PNG）とエフェクトを重ねてiframe描画する"""
    if not character_data:
        return

    is_image = isinstance(character_data, str)
    char_json_str = "null" if is_image else json.dumps(character_data)
    effect_json_str = json.dumps(effect_data) if effect_data else "null"

    if is_image:
        char_html = f'<img src="data:image/png;base64,{character_data}" style="position: absolute; width: 100%; height: 100%; object-fit: contain; z-index: 1;">'
    else:
        char_html = f'<div id="lottie-char-{key}" style="position: absolute; width: 100%; height: 100%; z-index: 1;"></div>'

    html_code = f"""
    <style>html, body {{ margin: 0; padding: 0; overflow: hidden; background: transparent; height: 100%; }}</style>
    <div style="position: relative; width: 100%; height: {height}px; display: flex; justify-content: center; align-items: center; overflow: hidden; background: transparent;">
        {char_html}
        <div id="lottie-effect-{key}" style="position: absolute; width: 100%; height: 100%; z-index: 2; pointer-events: none;"></div>
    </div>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/lottie-web/5.12.2/lottie.min.js"></script>
    <script>
        var charData = {char_json_str};
        if (charData) {{
            lottie.loadAnimation({{ container: document.getElementById('lottie-char-{key}'), renderer: 'svg', loop: true, autoplay: true, animationData: charData }});
        }}
        var effectData = {effect_json_str};
        if (effectData) {{ 
            lottie.loadAnimation({{ container: document.getElementById('lottie-effect-{key}'), renderer: 'svg', loop: false, autoplay: true, animationData: effectData }}); 
        }}
    </script>
    """
    data_url = f"data:text/html;charset=utf-8,{urllib.parse.quote(html_code)}"
    st.iframe(src=data_url, height=height)


def render_line_message(role: str, content: str, student_name: str, level: int):
    """LINE風のチャットUIメッセージをレンダリングする"""
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
        avatar_path = "resource/bird.png" if level >= 10 else "resource/egg.png"
        img_base64 = get_image_as_base64(avatar_path)
        
        if img_base64:
            avatar_content = f'<img src="data:image/png;base64,{img_base64}" style="width:100%; height:100%; border-radius:50%; object-fit:cover;">'
        else:
            avatar_content = "🐦" if level >= 10 else "🥚"
            
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
    """隠れ実績解除時に右上にカスタムアニメーショントーストを表示する"""
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