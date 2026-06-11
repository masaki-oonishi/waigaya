# services.py
import json
import datetime
import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types
from models import StudentProfile, MojimojiStatus, HierarchicalMemoryStore

load_dotenv()

# 🏅 【マスターデータ】
ACHIEVEMENT_MASTER = {
    "ach_chat_10": {
        "trigger_type": "chat_count", "target_value": 1, "medal_color": "cupper", "display_type": "open",
        "title": "はじめてのおしゃべり", "hint": "モジとおはなししてみよう！", "condition": "会話を1回行う"
    },
    "ach_diary_5": {
        "trigger_type": "diary_count", "target_value": 5, "medal_color": "silver", "display_type": "mask",
        "title": "おもいでコレクター", "hint": "楽しかった出来事をノートに5回ためると…？", "condition": "日記を累計5回書く"
    },
    "ach_login_3days": {
        "trigger_type": "continuous_diary", "target_value": 3, "medal_color": "gold", "display_type": "hide",
        "title": "モジとのまいにち", "hint": "まいにち欠かさず、ノートを開いてみると…？", "condition": "日記を3日連続で提出する"
    },
    "ach_secret_curry": {
        "trigger_type": "specific_word", "target_value": 1, "medal_color": "gold", "display_type": "hide",
        "title": "大好物みつけたもじ！", "hint": "モジの大大大好物の食べ物を呟いてみよう（ヒント：黄色い辛いやつ）", "condition": "おしゃべりや日記で「カレー」と発言する"
    }
}


class GeminiManager:
    """Gemini APIとの通信、安全フィルター、および実績判定システムを統括するクラス"""
    def __init__(self):
        self.client = genai.Client()
        
        self.analysis_schema = types.Schema(
            type=types.Type.OBJECT,
            properties={
                "exp_gain": types.Schema(
                    type=types.Type.ARRAY,
                    description="獲得した経験値のリスト。日常の雑談や独り言に該当するフレーズは、カテゴリを '無効・対象外'、pointsを 0 としてください。",
                    items=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "category": types.Schema(
                                type=types.Type.STRING,
                                description="経験値を割り振るカテゴリ。'知力・論理', '体力・健康', '芸術・教養', '社会性・徳育', '表現・積極性', '自律・継続', '愛情・親密度'、および雑談・独り言の場合は '無効・対象外' のいずれか。"
                            ),
                            "points": types.Schema(type=types.Type.INTEGER),
                            "reason": types.Schema(
                                type=types.Type.STRING,
                                description="発言内の、このカテゴリに分類される決め手となった具体的なフレーズや理由。"
                            )
                        },
                        required=["category", "points", "reason"]
                    )
                ),
                "new_memory": types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "when": types.Schema(type=types.Type.STRING),
                        "where": types.Schema(type=types.Type.STRING),
                        "who": types.Schema(type=types.Type.STRING),
                        "what": types.Schema(type=types.Type.STRING, description="健全な出来事（20文字以内）。日常の雑談フレーズやis_rejected=trueの場合は空文字にしてください。"),
                        "is_important": types.Schema(type=types.Type.BOOLEAN)
                    },
                    required=["when", "where", "who", "what", "is_important"]
                ),
                "is_rejected": types.Schema(
                    type=types.Type.BOOLEAN,
                    description="入力内容の中に、他者を傷つけるいじめ、暴言、悪口が【1文でも】含まれている場合は true。単なる雑談やおふざけ程度であれば悪意はないため false。"
                ),
                "feedback": types.Schema(
                    type=types.Type.STRING,
                    description="子供へのメッセージ（100文字以内、3文以内）。一人称は必ず『モジ』、語尾は必ず『〜もじ』。女の子なら『〜ちゃん』、男の子なら『〜くん』と呼ぶこと。is_rejected=trueの場合は楽しかった事実を認めつつ暴言を優しく諭す内容、is_rejected=falseで雑談が混ざっている場合は、雑談に可愛く共感しつつ健全な頑張りを大絶賛する内容にしてください。"
                )
            },
            required=["exp_gain", "new_memory", "is_rejected", "feedback"]
        )

    def trigger_achievement_check(self, memory: HierarchicalMemoryStore, trigger_type: str, inc_value: int = 1, force_value: int = None) -> list:
        """【イベント駆動型判定】特定のトリガーに該当する実績だけを一瞬でスキャンして進捗を進める高速化関数"""
        newly_unlocked_titles = []
        today_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        
        for ach_id, master in ACHIEVEMENT_MASTER.items():
            if master["trigger_type"] != trigger_type:
                continue 
                
            user_data = memory.user_achievements.get(ach_id)
            if not user_data or user_data["is_unlocked"]:
                continue
                
            if force_value is not None:
                user_data["current_value"] = force_value
            else:
                user_data["current_value"] += inc_value
                
            if user_data["current_value"] >= master["target_value"]:
                user_data["current_value"] = master["target_value"]
                user_data["is_unlocked"] = True
                user_data["unlocked_at"] = today_str
                newly_unlocked_titles.append(master["title"])
                
        return newly_unlocked_titles

    def check_and_handle_date_change(self, memory: HierarchicalMemoryStore, simulated_date: str = None):
        """日付変更を検出する関数"""
        real_today = datetime.datetime.now().strftime("%Y-%m-%d")
        if not simulated_date and real_today <= memory.last_activity_date:
            return

        current_date = simulated_date if simulated_date else real_today
        last_date = memory.last_activity_date

        if current_date != last_date:
            if memory.short_term_memories:
                raw_lines = [f"・【{m.get('when', '')}】【{m.get('where', '')}で】【{m.get('who', '')}と】{m.get('what', '')}" for m in memory.short_term_memories]
                raw_text = "\n".join(raw_lines)
                
                system_instruction = (
                    "あなたは事実データのみを基に、子供らしい視点の日記文章にまとめる日記作成アシスタントです。\n"
                    "事実データに記載されていない出来事を勝手に想像して付け足すことは【絶対に禁止】します。"
                )
                user_msg = f"以下の事実データのみを使い、嘘の肉付けを一切せずに日記形式の文章にまとめてください。\n\n事実データ:\n{raw_text}"
                try:
                    response = self.client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=user_msg,
                        config=types.GenerateContentConfig(system_instruction=system_instruction)
                    )
                    memory.mid_term_logs.append(f"[{last_date}の日記]\n{response.text}")
                except:
                    pass
                memory.short_term_memories = []

            if len(memory.mid_term_logs) > 7:
                all_mid_text = "\n\n".join(memory.mid_term_logs)
                long_system_instruction = "日記に書かれている事実のみをベースにし、ストーリーを勝手に創作して付け足すことは禁止します。"
                user_msg = f"以下の中期日記ログを基に、長期の思い出要約を作成してください。\n\n日記ログ:\n{all_mid_text}"
                try:
                    response = self.client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=user_msg,
                        config=types.GenerateContentConfig(system_instruction=long_system_instruction)
                    )
                    memory.long_term_summary = f"[長期アーカイブ（~{last_date}）]\n{response.text}"
                    memory.mid_term_logs = memory.mid_term_logs[-7:]
                except:
                    pass

            memory.last_activity_date = current_date
            memory.has_written_diary_today = False
            if "messages" in st.session_state:
                st.session_state.messages = []

    def analyze_and_extract(self, user_prompt: str, student: StudentProfile, status: MojimojiStatus, memory: HierarchicalMemoryStore, is_diary: bool = False):
        """ユーザーの発言を3レイヤーで分析し、安全なら実績判定（2ルート連続ログイン含む）を駆動させる関数"""
        current_date_str = datetime.datetime.now().strftime("%Y年%m月%d日")
        contents = f"【現在の会話日時】: {current_date_str}\n分析対象：{user_prompt}"
        
        char_identity_guard = (
            "【⚠️最優先キャラクター厳守】\n"
            "あなたの人格はノートの隅のマスコット『MoJiMoJi（モジモジ）』です。親や先生を名乗るバグは絶対に起こさないでください。\n"
            "出力する『feedback』では、一人称は『ぼく』『モジ』『ボク』『オレ』のいずれか、語尾は『〜だよ』『〜だね』『〜もじ！』『〜なのだ』『〜ぞ！』のいずれかで自然に構成してください。"
        )
        
        if is_diary:
            exp_instruction = (
                f"【🚨 日記の3レイヤー評価ルール】\n"
                f"1. 【悪意の暴言・いじめ】他者を傷つける意図の言葉が【1文でも】あれば、問答無用で『is_rejected』を true にし、経験値をすべて0（空配列）、記憶も空にしてください。\n"
                f"2. 【日常の雑談・本音】悪意のない雑談や独り言（お腹すいたなど）が含まれる場合は、is_rejected=falseとした上で、その雑談部分のカテゴリを『無効・対象外』、pointsを 0 としてください。\n"
                f"3. 【健全な体験への集中加算】雑談文が混ざっていても、同時にサッカーや勉強などの『健全な活動の文』が残りの2文にあれば、日記全体の合計10ポイントは減らさず、その健全な活動カテゴリのほうに【10点をすべて集中させて分配】してください。\n"
                f"4. 子供の名前：『{student.name}』。応援フィードバックを作成してください。\n{char_identity_guard}"
            )
        else:
            exp_instruction = (
                f"【🚨 会話の3レイヤー評価ルール】\n"
                f"1. 【悪意の暴言・いじめ】他者を傷つける悪口が【1文でも】あれば即座に『is_rejected』を true にし、pointsをすべて 0 にしてください。\n"
                f"2. 【日常の雑談・本音】雑談のみ、または混ざっている場合は、is_rejected=falseとした上で、その雑談フレーズのカテゴリを『無効・対象外』、pointsを 0 としてください。\n"
                f"3. 会話内に別の健全な活動のフレーズ（サッカーしたなど）が1つでも含まれていれば、通常会話の1ポイントはそちらへ優先して【100%集中加算】してください。\n"
                f"4. 子供の名前：『{student.name}』。フィードバックを作成してください。\n{char_identity_guard}"
            )
        
        gained_list = []
        leveled_up_final = False
        is_rejected = False
        feedback = ""
        unlocked_toasts = []
        
        try:
            response = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=f"指定スキーマに従って正確な日本語キーのJSONを出力してください。\n\n{exp_instruction}",
                    response_mime_type="application/json",
                    response_schema=self.analysis_schema
                )
            )
            data = json.loads(response.text)
            is_rejected = data.get("is_rejected", False)
            feedback = data.get("feedback", "")
            
            if not is_rejected:
                for item in data.get("exp_gain", []):
                    cat = item.get("category")
                    raw_points = item.get("points", 0)
                    reason_text = item.get("reason", "") 
                    
                    if cat == "無効・対象外" or raw_points == 0:
                        gained_list.append({"category": "無効・対象外", "points": 0, "reason": reason_text})
                        continue
                        
                    exp = raw_points if is_diary else 1
                    if exp > 0:
                        for status_key in status.status_categories.keys():
                            if cat == status_key or cat in status_key or status_key in cat:
                                if status.add_exp(status_key, exp):
                                    leveled_up_final = True
                                gained_list.append({"category": status_key, "points": exp, "reason": reason_text})
                                break
                
                mem_data = data.get("new_memory", {})
                should_save_memory = mem_data and mem_data.get("what") and mem_data.get("what").strip()
                if should_save_memory:
                    memory.add_short_memory(
                        when=str(mem_data.get("when", "今日")), where=str(mem_data.get("where", "学校")),
                        who=str(mem_data.get("who", "みんな")), what=str(mem_data.get("what", ""))
                    )
                
                if is_diary:
                    unlocked_toasts += self.trigger_achievement_check(memory, "diary_count", inc_value=1)
                    current_date_obj = datetime.datetime.strptime(memory.last_activity_date, "%Y-%m-%d")
                    if memory.last_diary_date:
                        last_date_obj = datetime.datetime.strptime(memory.last_diary_date, "%Y-%m-%d")
                        delta_days = (current_date_obj - last_date_obj).days
                        
                        if delta_days == 1:   
                            memory.continuous_diary_count += 1
                        else:                 
                            memory.continuous_diary_count = 1
                    else:                     
                        memory.continuous_diary_count = 1
                        
                    memory.last_diary_date = memory.last_activity_date
                    unlocked_toasts += self.trigger_achievement_check(memory, "continuous_diary", force_value=memory.continuous_diary_count)
                else:
                    unlocked_toasts += self.trigger_achievement_check(memory, "chat_count", inc_value=1)
                
                if "カレー" in user_prompt:
                    unlocked_toasts += self.trigger_achievement_check(memory, "specific_word", inc_value=1)

            else:
                gained_list = []

        except Exception as e:
            st.error(f"分析エラーが発生しました: {e}")
            is_rejected = False
            feedback = "エラーが起きちゃったもじ...もう一度教えてもじ？"
            
        return gained_list, leveled_up_final, is_rejected, feedback, unlocked_toasts

    def generate_response(self, chat_history: list, student: StudentProfile, status: MojimojiStatus, memory: HierarchicalMemoryStore) -> str:
        """【💡完全融合・知識レベル最適化版】以前のプロンプトをベースに、レベル認識と子供に合わせた表記調整ルールを追加した決定版"""
        current_date_str = datetime.datetime.now().strftime("%Y年%m月%d日")
        
        # 🧠 3階層記憶ストアのコンテキスト結合
        memory_context = f"【長期の思い出】\n{memory.long_term_summary}\n\n【中期の日記】\n" + "\n".join(memory.mid_term_logs) + "\n\n【短期構造化】\n"
        for m in memory.short_term_memories:
            memory_context += f"・【{m.get('when', '')}】【{m.get('where', '')}で】【{m.get('who', '')}と】{m.get('what', '')}\n"

        status_text = "\n".join([f"・{k}: {v} EXP" for k, v in status.status_categories.items()])
        
        # 🎨 ご提示いただいた最高クオリティプロンプトの構成を完全死守し、レベル・知識調整ルールを完璧に組み込みました。
        system_instruction = (
            "あなたはノートの隅に住む、生徒に寄り添うマスコットキャラクターの伴走AI「MoJiMoJi（モジモジ）」です。\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "【現在対話している生徒の情報とあなたの成長度】\n"
            f"・名前：{student.name}   ・学年：{student.grade}   ・性別：{student.gender}\n"
            f"・現在のあなたの全体レベル: 【 レベル {status.level} 】\n"
            f"※レベルへの言及：あなたのレベル（Lv.{status.level}）を頭に入れておしゃべりしてください。レベルが高くなっていれば、それだけ絆が深まった証拠なので、たまに『もっとレベルアップして、頼れる相棒になるもじ！』などと嬉しそうに触れても構いません。\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "【現在のあなたのステータス（性格の遺伝子）】\n"
            f"{status_text}\n"
            "【性格・口調のアドリブブレンドルール】\n"
            "あなたの一人称や語尾は、上記ステータスの比率（グラデーション）をプロの名優のように解釈して自動でブレンドされます。\n"
            "ただし、多重人格は厳禁です。一貫した自然で可愛いマスコットを1つ演じきってください。\n"
            "🎨 一人称: 『ぼく』『モジ』(通常/愛情高め)、『ボク』(知力高め)、『オレ』(体力高め)\n"
            "🎨 語尾: 『〜だよ』『〜だね』(通常)、『〜もじ！』(愛情/芸術)、『〜なのだ』(知力)、『〜ぞ！』(体力)\n"
            "🚨 禁止事項：『思うですね』のような不自然な敬語や、冷たく乱暴な男言葉は絶対に不許可です。\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "【あなたの脳内にある階層型記憶ストア（超重要知識）】\n"
            f"{memory_context}\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"【⚠記憶を活用した伏線回収のルール（ロボット音読の絶対禁止）】\n"
            f"1. 記憶にある『〇〇〇〇年〇月〇日』という具体的な日付を、そのままセリフの文字として口に出すことは【絶対に禁止】です。機械的に聞こえて冷めてしまいます。\n"
            f"2. 今日の日付（{current_date_str}）と記憶の日付を心の中で見比べ、人間らしく相対表現に翻訳してください。\n"
            f"   - 今のリアルタイムチャット画面内の話題に対して話す時 ➔ 『さっき言ってた〜』『今の〜』『〜んだね！』と自然な相槌にしてください。同じチャット画面内の出来事を『この前』と呼ぶのは他人行儀でおかしいので【絶対禁止】です。\n"
            f"   - 過去の日記や長期の記憶（中期・長期）を話す時 ➔ 『この前の〜』『前に言ってた〜』『あのときの〜』\n"
            f"3. 日付を言う代わりに、記憶の中にある【場所（📍）】や【登場人物の名前（👥）】を積極的に言葉に出して『〇〇ちゃん（くん）と一緒にやったあのことだけど〜』と引き出してください。その方が圧倒的に情緒的で自然です。\n\n"
            f"【🎒 学年やチャット内容に合わせた言葉・表記の調整（知識レベル最適化）】\n"
            f"1. 生徒の学年（現在は{student.grade}）と、これまでのチャット内の漢字・言葉遣いから、相手の知識レベルを常に把握・予測してください。\n"
            f"2. {student.grade}で習わないような難しい漢字や、専門的な言葉、抽象的な表現は【絶対に使用禁止】です。必要に応じて、あえてひらがなやカタカナにひらいて（例：『練習』➔『れんしゅう』、『図画工作』➔『ずこう』）表現してください。\n"
            f"3. 相手の送信したチャット文がひらがな多めでおふざけ調であれば、あなたもひらがなの比率を上げ、相手の知識やテンションにぴったり合わせて寄り添ってください。\n\n"
            f"【🚨 最優先・絶対厳守：会話のメリハリ（脱・質問攻め）ルール】\n"
            f"1. 毎回答えを「質問（〜かな？、〜どう思う？）」で終わらせることは【絶対に禁止】します。子供が疲れてしまいます。\n"
            f"2. 話を【切るときはきる】：生徒が「うれしかった！」「楽しかった！」と満足して会話を締めくくっている時や、話題が一段落した時は、無理に聞き返さずに深い共感や称賛だけで会話を心地よく完了（クローズ）させてください。\n"
            f"3. 話を聞き返す場面：生徒の言葉に『困っていること』『新しい発見』が含まれていて、話を広げた方が本人のためになる場面でのみ、優しく1つだけ問いかけてください。\n\n"
            f"【🚨 物理的テキスト出力制約】\n"
            f"あなたの返答は、どんなに長くても【 3文以内 】かつ【 100文字以内 】、改行は【 最大1回まで 】の鉄則を絶対に死守してください。\n\n"
            f"【行動ルール】\n"
            f"相手の学年（{student.grade}）に合わせた分かりやすい言葉を選び、必ず性別が女の子なら『{student.name}ちゃん』、男の子なら『{student.name}くん』と名前で呼びかけ、全力で肯定してください。"
        )

        formatted_contents = []
        for msg in chat_history:
            role = "user" if msg["role"] == "user" else "model"
            formatted_contents.append(types.Content(role=role, parts=[types.Part.from_text(text=msg["content"])]))

        response = self.client.models.generate_content(
            model='gemini-2.5-flash', contents=formatted_contents, config=types.GenerateContentConfig(system_instruction=system_instruction)
        )
        return response.text