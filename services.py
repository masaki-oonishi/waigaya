# services.py
import json
import datetime
import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types
from models import StudentProfile, MojimojiStatus, HierarchicalMemoryStore

load_dotenv()


class GeminiManager:
    """Gemini APIとの通信、構造化分析、および安全フィルター（一括無効・雑談受け流し）を統括するクラス"""
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

    def check_and_handle_date_change(self, memory: HierarchicalMemoryStore, simulated_date: str = None):
        """日付変更を検出し、記憶を中期➔長期へと圧縮ロールアップし、日記制限とチャット表示をクリアする関数"""
        current_date = simulated_date if simulated_date else datetime.datetime.now().strftime("%Y-%m-%d")
        last_date = memory.last_activity_date

        if current_date != last_date:
            if memory.short_term_memories:
                raw_lines = [f"・【{m.get('when', '')}】【{m.get('where', '')}で】【{m.get('who', '')}と】{m.get('what', '')}" for m in memory.short_term_memories]
                raw_text = "\n".join(raw_lines)
                
                system_instruction = (
                    "あなたは与えられた事実データのみを基に、子供らしい視点の日記文章にまとめる日記作成アシスタントです。\n"
                    "【⚠️絶対厳守ルール：妄想や創作の完全禁止】\n"
                    "事実データに記載されていない出来事、具体的な名前、虫や物の様子、会話、エピソードなどを勝手に想像して付け足すことは【絶対に禁止】します。\n"
                    "元の情報が少ない場合は、無理に引き伸ばさず、事実だけを述べた短い日記にしてください。最大でも400文字以内とし、事実の量に合わせた長さに留めてください。"
                )
                
                user_msg = f"以下の事実データのみを使い、嘘の肉付けを一切せずに日記形式の文章（最大400文字以内）にまとめてください。\n\n事実データ:\n{raw_text}"
                
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
                
                long_system_instruction = (
                    "あなたは複数の日記を1つの長期思い出要約にまとめるアシスタントです。\n"
                    "日記に書かれている事実のみをベースにし、そこにないストーリーや設定を勝手に創作して付け足すことは【絶対に禁止】します。最大600文字以内で事実に忠実にまとめてください。"
                )
                
                user_msg = f"以下の中期日記ログを基に、創作を一切交えずに長期の思い出要約（最大600文字以内）を作成してください。\n\n日記ログ:\n{all_mid_text}"
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
        """ユーザーの発言を分析し、いじめは全無効、雑談は部分無視して健全な体験に点数を全集中させる関数"""
        current_date_str = datetime.datetime.now().strftime("%Y年%m月%d日")
        contents = f"【現在の会話日時】: {current_date_str}\n分析対象：{user_prompt}"
        
        char_identity_guard = (
            "【⚠️最優先キャラクター厳守】\n"
            "あなたの人格はノートの隅のマスコット『MoJiMoJi（モジモジ）』です。親や先生、システム管理者を名乗るバグは絶対に起こさないでください。\n"
            "出力する『feedback』では、一人称は必ず『モジ』、語尾は必ず『〜もじ』にしてください。"
        )
        
        if is_diary:
            exp_instruction = (
                f"【🚨 日記の3レイヤー評価ルール】\n"
                f"1. 【悪意の暴言・いじめ】他者を傷つける意図の言葉が【1文でも】あれば、問答無用で『is_rejected』を true にし、経験値をすべて0（空配列）、記憶も空にしてください。（※友達を助けた話は除く）\n"
                f"2. 【日常の雑談・本音】悪意のない雑談や独り言（お腹すいた、眠いなど）が含まれる場合は、is_rejected=falseとした上で、その雑談部分のカテゴリを『無効・対象外』、pointsを 0 としてください。\n"
                f"3. 【健全な体験への集中加算】雑談文が混ざっていても、同時にサッカーや勉強などの『健全な活動の文』が残りの2文にあれば、日記全体の合計10ポイントは減らさず、その健全な活動カテゴリのほうに【10点をすべて集中させて分配】してください。\n"
                f"4. 子供の名前：『{student.name}』。頑張りを大絶賛しつつ雑談にも可愛く触れる『feedback』を必ず作成してください。\n"
                f"{char_identity_guard}"
            )
        else:
            exp_instruction = (
                f"【🚨 会話の3レイヤー評価ルール】\n"
                f"1. 【悪意の暴言・いじめ】他者を傷つける悪口が【1文でも】あれば即座に『is_rejected』を true にし、pointsをすべて 0 にしてください。\n"
                f"2. 【日常の雑談・本音】「お腹すいた」「眠いな」「うん」などの雑談のみ、または混ざっている場合は、is_rejected=falseとした上で、その雑談フレーズのカテゴリを『無効・対象外』、pointsを 0 としてください。\n"
                f"3. 会話内に別の健全な活動・体験のフレーズ（サッカーした、宿題したなど）が1つでも含まれていれば、通常会話の1ポイントはそちらの健全カテゴリへ優先して【100%集中加算】し、記憶（new_memory）もそちらから正確に抽出してください。\n"
                f"4. 子供の名前：『{student.name}』。条件に応じた『feedback』を必ず作成してください。\n"
                f"{char_identity_guard}"
            )
        
        gained_list = []
        leveled_up_final = False
        is_rejected = False
        feedback = ""
        
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
                    
                    # 💡 【日常雑談の部分スルー処理】
                    # 「無効・対象外」カテゴリ（雑談フレーズ）だった場合は、ステータスEXPの加算処理だけを綺麗にスキップします。
                    # ただし、ダッシュボードのタイムラインには「スルーされた理由」として可視化するため、0点データとして履歴配列にだけは追加します。
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
                        when=str(mem_data.get("when", "今日") if mem_data.get("when") else "今日"),
                        where=str(mem_data.get("where", "学校やお家") if mem_data.get("where") else "学校やお家"),
                        who=str(mem_data.get("who", "みんな") if mem_data.get("who") else "みんな"),
                        what=str(mem_data.get("what", ""))
                    )
            else:
                gained_list = []

        except Exception as e:
            st.error(f"分析エラーが発生しました: {e}")
            print(f"[詳細エラーログ] {e}")
            is_rejected = False
            feedback = "エラーが起きちゃったもじ...もう一度教えてもじ？"
            
        return gained_list, leveled_up_final, is_rejected, feedback

    def generate_response(self, chat_history: list, student: StudentProfile, status: MojimojiStatus, memory: HierarchicalMemoryStore) -> str:
        """チャットの全履歴(chat_history)を丸ごと読み込み、完璧に時間軸と文脈を同期させた可愛い返答を生成する関数"""
        current_date_str = datetime.datetime.now().strftime("%Y年%m月%d日")
        
        memory_context = f"【長期の思い出】\n{memory.long_term_summary}\n\n【中期の日記】\n" + "\n".join(memory.mid_term_logs) + "\n\n【短期構造化】\n"
        for m in memory.short_term_memories:
            memory_context += f"・【{m.get('when', '')}】【{m.get('where', '')}で】【{m.get('who', '')}と】{m.get('what', '')}\n"

        status_text = "\n".join([f"・{k}: {v} EXP" for k, v in status.status_categories.items()])
        
        system_instruction = (
            f"あなたはノートの隅に住むマスコットAI「MoJiMoJi（モジモジ）」です。ひらがなやカタカナを交えて、子供が喜ぶ可愛いトーンで話します。\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"【👤 話している生徒のプロフィール】\n"
            f"・お名前：{student.name}\n"
            f"・学年 ：{student.grade}\n"
            f"・性別 ：{student.gender}\n"
            f"※呼びかけのルール：性別が『女の子』なら『{student.name}ちゃん』、『男の子』なら『{student.name}くん』と呼んでください。\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"【🚨 最優先・絶対厳守：会話のメリハリ（脱・質問攻め）ルール】\n"
            f"1. 毎回答えを「質問（〜かな？、〜どう思う？）」で終わらせることは【絶対に禁止】します。子供が疲れてしまいます。\n"
            f"2. 話を【切るときはきる】：\n"
            f"   生徒が「うれしかった！」「楽しかった！」と満足して会話を締めくくっている時や、話題が一段落した時は、無理に聞き返さずに「モジも嬉しいもじ！」「応援してるもじ！」と深い共感や称賛だけで会話を心地よく完了（クローズ）させてください。\n"
            f"3. 話を【聞き返す場面】：\n"
            f"   生徒の言葉に『困っていること』『新しい発見』『もっと知りたい意欲』が含まれていて、話を広げた方が本人のためになる場面でのみ、優しく1つだけ問いかけてください。\n"
            f"4. あなたの返答は、どんなに長くても【 3文以内 】かつ【 100文字以内 】、改行は【 最大1回まで 】の鉄則を維持してください。\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"【🚨 時間軸と表現のルール（重要）】\n"
            f"1. 今まさに上のチャット履歴内で行われているリアルタイムの話題に対しては、『さっき言ってた〜』や『〜んだね！』『そうもじね！』と、普通のチャットの自然な相槌として返答してください。同じチャット画面内の出来事を『この前』と呼ぶのは他人行儀でおかしいので【絶対禁止】です。\n"
            f"2. 脳内記憶（過去の日記ログや長期の思い出）にある、以前の活動データを引っ張り出して伏線回収するときのみ、『この前』『あのとき』と表現してください。\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"【口調・記憶・📊現在の成長度ルール】\n"
            f"・現在のあなたの全体レベル: 【 レベル {status.level} 】\n"
            f"・現在のあなたのステータス（カテゴリ別内訳）:\n{status_text}\n"
            f"・脳内記憶:\n{memory_context}\n"
            f"・『〇年〇月〇日』などの日付を直接口にするのはロボット風で興ざめするので絶対禁止。今日（{current_date_str}）と見比べ自然に翻訳して伏線回収してください。"
        )

        formatted_contents = []
        for msg in chat_history:
            role = "user" if msg["role"] == "user" else "model"
            formatted_contents.append(
                types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=msg["content"])]
                )
            )

        response = self.client.models.generate_content(
            model='gemini-2.5-flash',
            contents=formatted_contents,
            config=types.GenerateContentConfig(system_instruction=system_instruction)
        )
        return response.text