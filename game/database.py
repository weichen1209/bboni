"""
排行榜資料庫模組
"""

import sqlite3
import os
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime


@dataclass
class LeaderboardEntry:
    """排行榜紀錄"""
    id: int
    nickname: str
    total_score: int
    grade: str
    purity: int
    uniformity: int
    exposure: int
    precision: int
    created_at: datetime


class LeaderboardDB:
    """排行榜資料庫管理器"""

    def __init__(self, db_path: str = None):
        """初始化資料庫"""
        if db_path is None:
            # 預設路徑：專案根目錄下的 data/leaderboard.db
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.db_path = os.path.join(base_dir, "data", "leaderboard.db")
        else:
            self.db_path = db_path

        self._ensure_data_dir()
        self._init_db()

    def _ensure_data_dir(self):
        """確保資料目錄存在"""
        data_dir = os.path.dirname(self.db_path)
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)

    def _init_db(self):
        """初始化資料庫 schema"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS leaderboard (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nickname TEXT NOT NULL,
                    total_score INTEGER NOT NULL,
                    grade TEXT NOT NULL,
                    purity INTEGER NOT NULL,
                    uniformity INTEGER NOT NULL,
                    exposure INTEGER NOT NULL,
                    precision INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # 建立索引加速排序查詢
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_total_score
                ON leaderboard(total_score DESC)
            """)
            conn.commit()

    def add_record(self, nickname: str, total_score: int, grade: str,
                   scores: dict) -> int:
        """
        新增排行榜紀錄

        Args:
            nickname: 玩家暱稱
            total_score: 總分
            grade: 等級 (A/B/C/D)
            scores: 各項分數 dict，包含 purity, uniformity, exposure, precision

        Returns:
            新紀錄的 id
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO leaderboard
                (nickname, total_score, grade, purity, uniformity, exposure, precision)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                nickname,
                total_score,
                grade,
                int(scores.get("purity", 0)),
                int(scores.get("uniformity", 0)),
                int(scores.get("exposure", 0)),
                int(scores.get("precision", 0))
            ))
            conn.commit()
            return cursor.lastrowid

    def get_top_records(self, limit: int = 10) -> List[LeaderboardEntry]:
        """
        取得前 N 名紀錄

        Args:
            limit: 要取得的紀錄數量

        Returns:
            LeaderboardEntry 列表，按分數降序排列
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, nickname, total_score, grade,
                       purity, uniformity, exposure, precision, created_at
                FROM leaderboard
                ORDER BY total_score DESC, created_at ASC
                LIMIT ?
            """, (limit,))

            records = []
            for row in cursor.fetchall():
                # 解析時間戳記
                created_at = row["created_at"]
                if isinstance(created_at, str):
                    try:
                        created_at = datetime.fromisoformat(created_at)
                    except ValueError:
                        created_at = datetime.now()

                records.append(LeaderboardEntry(
                    id=row["id"],
                    nickname=row["nickname"],
                    total_score=row["total_score"],
                    grade=row["grade"],
                    purity=row["purity"],
                    uniformity=row["uniformity"],
                    exposure=row["exposure"],
                    precision=row["precision"],
                    created_at=created_at
                ))

            return records

    def get_player_rank(self, record_id: int) -> Optional[int]:
        """
        取得特定紀錄的排名

        Args:
            record_id: 紀錄 id

        Returns:
            排名 (1-based)，如果找不到則回傳 None
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # 先取得該紀錄的分數
            cursor.execute("""
                SELECT total_score, created_at FROM leaderboard WHERE id = ?
            """, (record_id,))
            result = cursor.fetchone()

            if not result:
                return None

            score, created_at = result

            # 計算排名：分數更高，或分數相同但時間更早的紀錄數 + 1
            cursor.execute("""
                SELECT COUNT(*) + 1 FROM leaderboard
                WHERE total_score > ?
                   OR (total_score = ? AND created_at < ?)
            """, (score, score, created_at))

            rank = cursor.fetchone()[0]
            return rank

    def get_record_by_id(self, record_id: int) -> Optional[LeaderboardEntry]:
        """
        根據 id 取得紀錄

        Args:
            record_id: 紀錄 id

        Returns:
            LeaderboardEntry 或 None
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, nickname, total_score, grade,
                       purity, uniformity, exposure, precision, created_at
                FROM leaderboard
                WHERE id = ?
            """, (record_id,))

            row = cursor.fetchone()
            if not row:
                return None

            created_at = row["created_at"]
            if isinstance(created_at, str):
                try:
                    created_at = datetime.fromisoformat(created_at)
                except ValueError:
                    created_at = datetime.now()

            return LeaderboardEntry(
                id=row["id"],
                nickname=row["nickname"],
                total_score=row["total_score"],
                grade=row["grade"],
                purity=row["purity"],
                uniformity=row["uniformity"],
                exposure=row["exposure"],
                precision=row["precision"],
                created_at=created_at
            )
