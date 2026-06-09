# services.py
import json
import datetime
import streamlit as st  # 💡 インポート漏れを修正
from dotenv import load_dotenv
from google import genai
from google.genai import types
from models import StudentProfile, MojimojiStatus, HierarchicalMemoryStore

# .envファイルから環境変数を読み込む
load_dotenv()


class GeminiManager:
    """Gemini APIとの通信、構造化分析、および階層記憶の要約エスカレーションを統括するクラス"""
    def __init__(self):
        self.client = genai.Client()
        
        # 💡 【修正】AIが正しい日本語キーを返すよう、description（指示）を再注入しました
        self.analysis_schema = types.Schema(
            type=types.Type.OBJECT,
            properties={
                "exp_gain": types.Schema(
                    type=types.Type.ARRAY,
                    description="獲得した経験値のリスト",
                    items=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "category": types.Schema(
                                type=types.Type.STRING,
                                description="経験値を割り振るカテゴリ。必ず次のいずれかと完全一致させてください: '知力・論理', '体力・健康', '芸術・教養', '社会性・徳育', '表現・積極性', '自律・継続', '愛情・親密度'"
                            ),
                            "points": types.Schema(
                                type=types.Type.INTEGER,
                                description="割り振る経験値（1〜5の整数）"
                            )
                        },
                        required=["category", "points"]
                    )
                ),
                "new_memory": types.Schema(
                    type=types.Type.OBJECT,
                    description="生徒の発言から新しく記憶すべき「いつ・どこで・誰と・何をしたか」のコンテキスト情報",
                    properties={
                        "when": types.Schema(
                            type=types.Type.STRING,
                            description="いつの出来事か。明確な時間情報がなければ提示された現在の年月日（〇〇〇〇年〇月〇日）を入れてください。"
                        ),
                        "where": types.Schema(
                            type=types.Type.STRING,
                            description="どこでの出来事か。特定できなければ空文字にしてください。"
                        ),
                        "who": types.Schema(
                            type=types.Type.STRING,
                            description="誰との出来事か。友達の名前や登場人物。特定できなければ空文字にしてください。"
                        ),
                        "what": types.Schema(
                            type=types.Type.STRING,
                            description="何をした、何を見た、どんな出来事があったか（20文字以内）。"
                        ),
                        "is_important": types.Schema(
                            type=types.Type.BOOLEAN,
                            description="これが永続的に記憶すべき大切な出来事である場合はtrue、雑談ならfalseにしてください。"
                        )
                    },
                    required=["when", "where", "who", "what", "is_important"]
                )
            },
            required=["exp_gain", "new_memory"]
        )

    def check_and_handle_date_change(self, memory: HierarchicalMemoryStore, simulated_date: str = None):
        """日付変更を検出し、記憶を中期・長期へとロールアップ（要約圧縮）する"""
        current_date = simulated_date if simulated_date else datetime.datetime.now().strftime("%Y-%m-%d")
        last_date = memory.last_activity_date

        if current_date != last_date:
            print(f"[デバッグ] 日付変更を検出しました: {last_date} ➔ {current_date}")
            
            # 1. 前日の短期構造化記憶をテキストの日記原稿にまとめる
            if memory.short_term_memories:
                raw_lines = [f"・【{m['when']}】【{m['where']}で】【{m['who']}と】{m['what']}" for m in memory.short_term_memories]
                raw_text = "\n".join(raw_lines)
                
                user_msg = (
                    "以下のテキストを400文字程度に日記形式で要約した文章を作成すること。このテキストは一日のユーザーとアシスタントの会話ログです。\n"
                    "作成する要約は会話の分析ではなく、会話ログにある出来事をまとめた要約です。特に固有名詞や、行動などは重視してください。\n"
                    "絵文字は無視してください。要約するテキスト=\n" + raw_text
                )
                
                try:
                    response = self.client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=user_msg,
                        config=types.GenerateContentConfig(system_instruction="あなたは賢いAIです。必ず日本語で要約だけを答えること。")
                    )
                    mid_summary = f"[{last_date}の日記]\n{response.text}"
                    
                    memory.mid_term_logs.append(mid_summary)
                    print(f"[デバッグ] 前日の短期記憶を中期ログに圧縮保存しました。")
                except Exception as e:
                    print(f"中期要約の作成に失敗しました: {e}")
                
                memory.short_term_memories = []

            # 2. 中期ログが1週間（7件）を超えたら、長期要約（600文字）へ圧縮
            if len(memory.mid_term_logs) > 7:
                print(f"[デバッグ] 中期ログが1週間を超えたため、長期要約をアップデートします。")
                all_mid_text = "\n\n".join(memory.mid_term_logs)
                
                user_msg = (
                    "以下のテキストを600文字程度に要約した文章を作成すること。このテキストは数週間分のユーザーとアシスタントの会話の要約集です。\n"
                    "作成する要約は時系列順に整理し、重要な出来事や継続的なテーマ、固有名詞などを重視してください。\n"
                    "絵文字は無視してください。要約するテキスト=\n" + all_mid_text
                )
                
                try:
                    response = self.client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=user_msg,
                        config=types.GenerateContentConfig(system_instruction="あなたは賢いAIです。必ず日本語で要約だけを答えること。")
                    )
                    memory.long_term_summary = f"[長期アーカイブ（~{last_date}）]\n{response.text}"
                    memory.mid_term_logs = memory.mid_term_logs[-7:]
                    print(f"[デバッグ] 長期記憶の圧縮要約が完了しました。")
                except Exception as e:
                    print(f"長期要約の作成に失敗しました: {e}")

            memory.last_activity_date = current_date

    def analyze_and_extract(self, user_prompt: str, status: MojimojiStatus, memory: HierarchicalMemoryStore):
        """ユーザーの発言を分析し、経験値と【短期構造化記憶】を保存する"""
        current_date_str = datetime.datetime.now().strftime("%Y年%m月%d日")
        contents = f"【現在の会話日時（参考用）】: {current_date_str}\n分析対象の発言：{user_prompt}"
        
        try:
            response = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction="あなたは有能な教育データ分析AIです。指定スキーマに従って正確な日本語キーのJSONを出力してください。",
                    response_mime_type="application/json",
                    response_schema=self.analysis_schema
                )
            )
            data = json.loads(response.text)
            
            print("[デバッグ分析成功]:", data)
            
            # 1. 経験値の加算
            for item in data.get("exp_gain", []):
                cat = item.get("category")
                exp = item.get("points", 0)
                
                for status_key in status.status_categories.keys():
                    if cat == status_key or cat in status_key or status_key in cat:
                        # 経験値を反映し、レベルアップした場合は画面に通知を出す
                        if status.add_exp(status_key, exp):
                            st.toast(f"🎉 MoJiMoJiがレベル **{status.level}** に上がったよ！", icon="✨")
                        break
            
            # 2. 短期記憶への追加
            mem_data = data.get("new_memory", {})
            if mem_data and mem_data.get("is_important") and mem_data.get("what"):
                memory.add_short_memory(
                    when=mem_data.get("when", "").strip(),
                    where=mem_data.get("where", "").strip(),
                    who=mem_data.get("who", "").strip(),
                    what=mem_data["what"].strip()
                )
        except Exception as e:
            st.error(f"分析エラーが発生しました: {e}")

    def generate_response(self, user_prompt: str, student: StudentProfile, status: MojimojiStatus, memory: HierarchicalMemoryStore) -> str:
        """短期・中期・長期のすべての記憶階層を織り交ぜて、自然な口調で返答を生成する"""
        current_date_str = datetime.datetime.now().strftime("%Y年%m月%d日")
        
        memory_context = "【1. 最近数ヶ月〜数年前の長期の記憶・思い出（最優先アーカイブ）】\n"
        memory_context += (memory.long_term_summary if memory.long_term_summary else "特になし") + "\n\n"
        
        memory_context += "【2. 過去1週間以内の日ごとの日記ログ（中期記憶）】\n"
        if memory.mid_term_logs:
            memory_context += "\n".join(memory.mid_term_logs) + "\n\n"
        else:
            memory_context += "特になし\n\n"
            
        memory_context += "【3. 本日（さっき）覚えたことのリスト（短期・構造化記憶）】\n"
        if memory.short_term_memories:
            for m in memory.short_term_memories:
                memory_context += f"・【{m['when']}】【{m['where']}で】【{m['who']}と】{m['what']}\n"
        else:
            memory_context += "特になし\n"

        status_text = "\n".join([f"・{k}: {v} EXP" for k, v in status.status_categories.items()])
        
        system_instruction = (
            "あなたはノートの隅に住む、生徒に寄り添うマスコットキャラクターの伴走AI「MoJiMoJi（モジモジ）」です。\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "【現在対話している生徒の情報】\n"
            f"・名前：{student.name}   ・学年：{student.grade}   ・性別：{student.gender}\n"
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
            f"【⚠️記憶を活用した伏線回収のルール（ロボット音読の絶対禁止）】\n"
            f"1. 記憶にある『〇〇〇〇年〇月〇日』という具体的な日付を、そのままセリフの文字として口に出すことは【絶対に禁止】です。機械的に聞こえて冷めてしまいます。\n"
            f"2. 今日の日付（{current_date_str}）と記憶の日付を心の中で見比べ、人間らしく相対表現に翻訳してください。\n"
            f"   - 今日の記憶（短期記憶）を話す時 ➔ 『さっき言ってた〜』『今日の〜』\n"
            f"   - 過去の日記や長期の記憶（中期・長期）を話す時 ➔ 『この前の〜』『前に言ってた〜』『あのときの〜』\n"
            f"3. 日付を言う代わりに、記憶の中にある【場所（📍）】や【登場人物の名前（👥）】を積極的に言葉に出して『〇〇ちゃんと一緒にやったあのことだけど〜』と引き出してください。その方が圧倒的に情緒的で自然です。\n\n"
            f"【行動ルール】\n"
            f"{student.grade}に合わせた分かりやすい言葉を選び、必ず『{student.name}ちゃん/くん』と名前で呼びかけ、全力で肯定してください。"
        )

        response = self.client.models.generate_content(
            model='gemini-2.5-flash',
            contents=user_prompt,
            config=types.GenerateContentConfig(system_instruction=system_instruction)
        )
        return response.text