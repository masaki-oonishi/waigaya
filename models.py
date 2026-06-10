# models.py
import datetime
from typing import List, Dict, Any

class StudentProfile:
    """生徒の基本情報を管理するクラス"""
    def __init__(self, name: str = "ひなた", grade: str = "小学4年生", gender: str = "女の子"):
        self.name = name
        self.grade = grade
        self.gender = gender


class MojimojiStatus:
    """MoJiMoJiのレベル、経験値、個性の計算を管理するクラス"""
    def __init__(self):
        self.level = 1
        self.current_exp = 0
        self.status_categories = {
            "知力・論理": 0, "体力・健康": 0, "芸術・教養": 0, "社会性・徳育": 0,
            "表現・積極性": 0, "自律・継続": 0, "愛情・親密度": 0
        }

    def get_next_level_exp(self) -> int:
        """【仕様】レベルアップに必要な経験値を『30』に完全固定"""
        return 30

    def add_exp(self, category: str, points: int) -> bool:
        """特定のカテゴリに経験値を加算し、全体プールにも追加する。レベルアップしたらTrueを返す"""
        if category in self.status_categories:
            self.status_categories[category] += points
            self.current_exp += points
            
            # レベルアップチェック
            leveled_up = False
            while self.current_exp >= self.get_next_level_exp():
                self.current_exp -= self.get_next_level_exp()
                self.level += 1
                leveled_up = True
            return leveled_up
        return False


class HierarchicalMemoryStore:
    """短期・中期・長期の階層型記憶および分類ログを管理するクラス"""
    def __init__(self):
        self.short_term_memories: List[Dict[str, Any]] = []
        self.mid_term_logs: List[str] = []
        self.long_term_summary: str = ""
        self.last_activity_date: str = datetime.datetime.now().strftime("%Y-%m-%d")
        self.has_written_diary_today: bool = False  
        self.classification_history: List[Dict[str, Any]] = []

    def add_short_memory(self, when: str, where: str, who: str, what: str):
        """今日の構造化記憶を追加（重複チェック付き）"""
        is_duplicate = any(m["what"] == what for m in self.short_term_memories)
        if not is_duplicate:
            self.short_term_memories.append({
                "when": when, "where": where, "who": who, "what": what
            })