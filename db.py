# -*- coding: utf-8 -*-
"""
数据库层 — 复用于桌面版 wage_book.pyw
适配说明：
  - 移除了 PySide6 依赖
  - DB 文件路径改为 App.get_application_config() 返回的路径
  - 字段尽量与桌面版一致，新增 shift_type/start_time/end_time/default_type
  - 模型变更：models 表新增 default_type；records 表新增 shift_type/start_time/end_time
"""
import os
import sqlite3
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

# ---------------------------------------------------------------------------
# 定点金额工具（复用于桌面版）
# ---------------------------------------------------------------------------
def calc_wage_fen(quantity: int, price_milli: int) -> int:
    """计件批工资 = 数量 × 计件单价，保留 2 位（分）。"""
    return _milli_to_fen(Decimal(quantity) * Decimal(price_milli))


def calc_hourly_wage_fen(hours: float, hourly_milli: int) -> int:
    """计时批工资 = 计费小时 × 时薪，保留 2 位（分）。"""
    return _milli_to_fen(Decimal(str(hours)) * Decimal(hourly_milli))


def _milli_to_fen(milli_dec: Decimal) -> int:
    """厘级金额（Decimal）→ 分（整数）：÷10 四舍五入。"""
    fen = milli_dec / Decimal(10)
    return int(fen.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def price_text(milli: int) -> str:
    """厘 → '0.080'（固定 3 位小数）。"""
    if milli is None:
        return "—"
    return "%0.3f" % (milli / 1000.0)


def hourly_text(milli: int) -> str:
    """厘 → '23.00'（固定 2 位小数）。"""
    if milli is None:
        return "—"
    return "%0.2f" % (milli / 1000.0)


def wage_text(fen: int) -> str:
    """分 → '240.00'（固定 2 位小数）。"""
    return "%0.2f" % (fen / 100.0)


def fmt_hours(v) -> str:
    """1 位小数的时长文本。"""
    return "%0.1f" % (float(v or 0))


# ---------------------------------------------------------------------------
# 数据库
# ---------------------------------------------------------------------------
def default_db_path() -> str:
    """DB 放在 App config 目录下，Android 上即 AppStorage。"""
    try:
        from kivy.app import App
        cfg = App.get_application_config()
        base = os.path.dirname(cfg)
    except Exception:
        base = os.path.expanduser(".")
    return os.path.join(base, "wage_book.db")


class Database:
    def __init__(self, path: str | None = None):
        self.path = path or default_db_path()
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self._init_tables()
        self._seed_if_empty()

    # ---- Schema 迁移 ----
    def _init_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS user (
                id         INTEGER PRIMARY KEY,
                name       TEXT    NOT NULL DEFAULT '',
                created_at TEXT    NOT NULL
            );

            CREATE TABLE IF NOT EXISTS records (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                date           TEXT    NOT NULL,
                shift_type     TEXT    NOT NULL DEFAULT 'day',
                start_time     TEXT,
                end_time       TEXT,
                work_hours     REAL    DEFAULT 0,
                master_hours   REAL    DEFAULT 0,
                overtime_hours REAL    DEFAULT 0,
                work_type      TEXT    DEFAULT '',
                part_model     TEXT    DEFAULT '',
                quantity       INTEGER DEFAULT 0,
                price_milli    INTEGER DEFAULT 0,
                wage_fen       INTEGER DEFAULT 0,
                wage_manual    INTEGER DEFAULT 0,
                charge_mode    INTEGER NOT NULL DEFAULT 0,
                charge_hours   REAL    NOT NULL DEFAULT 0,
                created_at     TEXT    DEFAULT (datetime('now','localtime'))
            );

            CREATE TABLE IF NOT EXISTS models (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                name         TEXT    NOT NULL UNIQUE,
                default_type TEXT    DEFAULT '',
                piece_milli  INTEGER NOT NULL DEFAULT 0,
                hourly_milli INTEGER NOT NULL DEFAULT 0,
                created_at   TEXT    DEFAULT (datetime('now','localtime')),
                updated_at   TEXT
            );

            CREATE TABLE IF NOT EXISTS model_price_log (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                model_id   INTEGER NOT NULL,
                fee_mode   TEXT    NOT NULL,
                old_price  INTEGER,
                new_price  INTEGER,
                changed_at TEXT    NOT NULL
            );
        """)

        # 旧库升级：补新增字段
        self._ensure_col("records", "shift_type",
                         "ALTER TABLE records ADD COLUMN shift_type TEXT NOT NULL DEFAULT 'day'")
        self._ensure_col("records", "start_time",
                         "ALTER TABLE records ADD COLUMN start_time TEXT")
        self._ensure_col("records", "end_time",
                         "ALTER TABLE records ADD COLUMN end_time TEXT")
        self._ensure_col("models", "default_type",
                         "ALTER TABLE models ADD COLUMN default_type TEXT DEFAULT ''")
        self._ensure_col("models", "updated_at",
                         "ALTER TABLE models ADD COLUMN updated_at TEXT")

        # 初始化 user 表（若为空则插入一条占位）
        n = self.conn.execute("SELECT COUNT(*) FROM user").fetchone()[0]
        if n == 0:
            self.conn.execute(
                "INSERT INTO user(id, name, created_at) VALUES(1, '', ?)",
                (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),))
        self.conn.commit()

    def _ensure_col(self, table: str, col: str, ddl: str):
        cols = [r[1] for r in
                self.conn.execute("PRAGMA table_info(%s)" % table).fetchall()]
        if col not in cols:
            self.conn.execute(ddl)

    def _seed_if_empty(self):
        n = self.conn.execute("SELECT COUNT(*) FROM records").fetchone()[0]
        if not n:
            seed = [
                ("2026-09-01", "day",  "08:00", "17:00", 8.0, 0.0, 0.0, "冷铆", "10800061", 3000, 80, 24000),
                ("2026-09-02", "day",  "08:00", "17:00", 8.0, 0.0, 0.0, "冷铆", "10800034", 3090, 80, 24720),
                ("2026-09-03", "day",  "08:00", "17:00", 8.0, 0.0, 0.0, "冷铆", "10800034", 3262, 80, 26096),
                ("2026-09-04", "day",  "08:00", "17:00", 9.0, 0.0, 1.0, "冷铆", "10800034", 2250, 80, 18000),
                ("2026-09-05", "night", "20:00", "04:00", 8.0, 0.0, 0.0, "冷铆", "10800034", 3300, 80, 26400),
                ("2026-09-06", "day",  "08:00", "17:00", 8.0, 0.0, 0.0, "冷铆", "10800034", 2017, 80, 16136),
                ("2026-09-07", "day",  "08:00", "17:00", 8.0, 0.0, 0.0, "",  "",  0,    0,     0),
            ]
            for r in seed:
                self.add_record(*r)
        m = self.conn.execute("SELECT COUNT(*) FROM models").fetchone()[0]
        if not m:
            for name, milli in (("10800061", 80), ("10800034", 80)):
                self.conn.execute(
                    "INSERT INTO models(name, default_type, piece_milli, hourly_milli) "
                    "VALUES(?,'',?,0)", (name, milli))
        self.conn.commit()

    # ---- 用户信息 ----
    def get_user(self):
        row = self.conn.execute("SELECT * FROM user WHERE id=1").fetchone()
        if not row:
            return {"name": ""}
        return {"id": row[0], "name": row[1], "created_at": row[2]}

    def set_user_name(self, name: str):
        self.conn.execute("UPDATE user SET name=? WHERE id=1", (name,))
        self.conn.commit()

    # ---- 增删改查 ----
    def add_record(self, date, shift_type, start_time, end_time,
                   work_hours, master_hours, overtime_hours,
                   work_type, part_model, quantity, price_milli, wage_fen,
                   wage_manual=0, charge_mode=0, charge_hours=0.0):
        cur = self.conn.execute(
            """INSERT INTO records
               (date, shift_type, start_time, end_time, work_hours,
                master_hours, overtime_hours, work_type, part_model,
                quantity, price_milli, wage_fen, wage_manual, charge_mode, charge_hours)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (date, shift_type, start_time, end_time, work_hours,
             master_hours, overtime_hours, work_type, part_model,
             quantity, price_milli, wage_fen, wage_manual, charge_mode, charge_hours))
        self.conn.commit()
        return cur.lastrowid

    def update_record(self, rid, date, shift_type, start_time, end_time,
                      work_hours, master_hours, overtime_hours,
                      work_type, part_model, quantity, price_milli, wage_fen,
                      wage_manual, charge_mode, charge_hours):
        self.conn.execute(
            """UPDATE records SET date=?, shift_type=?, start_time=?, end_time=?,
                 work_hours=?, master_hours=?, overtime_hours=?,
                 work_type=?, part_model=?, quantity=?, price_milli=?,
                 wage_fen=?, wage_manual=?, charge_mode=?, charge_hours=?
               WHERE id=?""",
            (date, shift_type, start_time, end_time, work_hours,
             master_hours, overtime_hours, work_type, part_model,
             quantity, price_milli, wage_fen, wage_manual, charge_mode, charge_hours, rid))
        self.conn.commit()

    def delete_record(self, rid):
        self.conn.execute("DELETE FROM records WHERE id=?", (rid,))
        self.conn.commit()

    def get_record(self, rid):
        row = self.conn.execute(
            "SELECT * FROM records WHERE id=?", (rid,)).fetchone()
        if not row:
            return None
        cols = [d[0] for d in self.conn.execute("SELECT * FROM records LIMIT 0").description]
        return dict(zip(cols, row))

    def list_records(self, month: str | None = None):
        if month:
            rows = self.conn.execute(
                "SELECT * FROM records WHERE substr(date,1,7)=? ORDER BY date, id",
                (month,)).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM records ORDER BY date, id").fetchall()
        cols = [d[0] for d in self.conn.execute("SELECT * FROM records LIMIT 0").description]
        return [dict(zip(cols, r)) for r in rows]

    def all_months(self):
        rows = self.conn.execute(
            "SELECT DISTINCT substr(date,1,7) FROM records ORDER BY 1 DESC").fetchall()
        return [r[0] for r in rows]

    # ---- 型号管理 ----
    def list_models(self):
        rows = self.conn.execute("SELECT * FROM models ORDER BY name").fetchall()
        cols = [d[0] for d in self.conn.execute("SELECT * FROM models LIMIT 0").description]
        return [dict(zip(cols, r)) for r in rows]

    def model_by_name(self, name):
        row = self.conn.execute("SELECT * FROM models WHERE name=?", (name,)).fetchone()
        if not row:
            return None
        cols = [d[0] for d in self.conn.execute("SELECT * FROM models LIMIT 0").description]
        return dict(zip(cols, row))

    def model_by_id(self, mid):
        row = self.conn.execute("SELECT * FROM models WHERE id=?", (mid,)).fetchone()
        if not row:
            return None
        cols = [d[0] for d in self.conn.execute("SELECT * FROM models LIMIT 0").description]
        return dict(zip(cols, row))

    def add_model(self, name, default_type, piece_milli, hourly_milli):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.conn.execute(
            "INSERT INTO models(name, default_type, piece_milli, hourly_milli, created_at) "
            "VALUES(?,?,?,?,?)", (name, default_type, piece_milli, hourly_milli, now))
        self.conn.commit()

    def update_model(self, mid, name, default_type, piece_milli, hourly_milli,
                     sync_history=True):
        """
        修改型号单价时，若 sync_history=True，自动回写所有历史明细。
        """
        # 读取旧值
        old = self.model_by_id(mid)
        if not old:
            return

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 同步历史明细（若单价变了）
        if sync_history and (piece_milli != old["piece_milli"] or
                             hourly_milli != old["hourly_milli"]):
            self._sync_model_history(mid, piece_milli, hourly_milli, old)

        # 写日志
        if piece_milli != old["piece_milli"]:
            self.conn.execute(
                "INSERT INTO model_price_log(model_id, fee_mode, old_price, new_price, changed_at) "
                "VALUES(?, 'piece', ?, ?, ?)",
                (mid, old["piece_milli"], piece_milli, now))
        if hourly_milli != old["hourly_milli"]:
            self.conn.execute(
                "INSERT INTO model_price_log(model_id, fee_mode, old_price, new_price, changed_at) "
                "VALUES(?, 'hourly', ?, ?, ?)",
                (mid, old["hourly_milli"], hourly_milli, now))

        # 更新型号表
        self.conn.execute(
            "UPDATE models SET name=?, default_type=?, piece_milli=?, "
            "hourly_milli=?, updated_at=? WHERE id=?",
            (name, default_type, piece_milli, hourly_milli, now, mid))
        self.conn.commit()

    def _sync_model_history(self, mid, new_piece, new_hourly, old):
        """把所有该型号的记录同步更新。"""
        model = self.model_by_id(mid)
        if not model:
            return
        name = model["name"]

        # 找出所有该型号的记录
        rows = self.conn.execute(
            "SELECT id, charge_mode, quantity, charge_hours, price_milli, wage_fen "
            "FROM records WHERE part_model=?", (name,)).fetchall()

        for rid, charge_mode, quantity, charge_hours, old_price, old_wage in rows:
            mode = int(charge_mode or 0)
            if mode == 0:  # 计件
                qty = int(quantity or 0)
                new_price = new_piece
                new_wage = calc_wage_fen(qty, new_piece) if new_piece else 0
            else:  # 计时
                hrs = float(charge_hours or 0)
                new_price = new_hourly
                new_wage = calc_hourly_wage_fen(hrs, new_hourly) if new_hourly else 0

            self.conn.execute(
                "UPDATE records SET price_milli=?, wage_fen=? WHERE id=?",
                (new_price, new_wage, rid))

        self.conn.commit()

    def model_usage_count(self, name):
        return self.conn.execute(
            "SELECT COUNT(*) FROM records WHERE part_model=?", (name,)).fetchone()[0]

    # ---- 月度统计 ----
    def monthly_summary(self, month: str):
        recs = self.list_records(month)
        daily = {}
        models = {}
        night_days = set()

        for r in recs:
            d = r["date"]
            if d not in daily:
                daily[d] = {"date": d, "hours": 0.0, "master": 0.0,
                            "overtime": 0.0, "wage_fen": 0}
            daily[d]["hours"] = max(daily[d]["hours"], float(r["work_hours"] or 0))
            daily[d]["master"] = max(daily[d]["master"], float(r["master_hours"] or 0))
            daily[d]["overtime"] = max(daily[d]["overtime"], float(r["overtime_hours"] or 0))
            daily[d]["wage_fen"] += int(r["wage_fen"] or 0)

            if r.get("shift_type") == "night":
                night_days.add(d)

            m = r["part_model"]
            if m:
                if m not in models:
                    models[m] = {"model": m, "quantity": 0, "wage_fen": 0}
                models[m]["quantity"] += int(r["quantity"] or 0)
                models[m]["wage_fen"] += int(r["wage_fen"] or 0)

        total_hours = round(sum(v["hours"] for v in daily.values()), 1)
        total_master = round(sum(v["master"] for v in daily.values()), 1)
        total_overtime = round(sum(v["overtime"] for v in daily.values()), 1)
        total_wage_fen = sum(v["wage_fen"] for v in daily.values())
        # 出勤天数：有记录保存的日期（含 wage=0）
        work_days = len(daily)
        return {
            "total_hours": total_hours,
            "total_master": total_master,
            "total_overtime": total_overtime,
            "total_wage_fen": total_wage_fen,
            "entries": len(recs),
            "work_days": work_days,
            "night_days": len(night_days),
            "daily": [daily[k] for k in sorted(daily)],
            "by_model": [models[k] for k in sorted(models)],
        }
