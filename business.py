# -*- coding: utf-8 -*-
"""
业务层 — 复用于桌面版 wage_book.pyw
只含计算/解析函数，无任何 UI 依赖。
"""
import re
from decimal import Decimal, ROUND_HALF_UP
from datetime import date

# ---------------------------------------------------------------------------
# 智能输入解析
# ---------------------------------------------------------------------------

WORK_TYPES = (
    "冷铆", "热铆", "焊接", "铆接",
    "焊接打样", "焊接工装", "焊接试制", "热铆打样",
    "冲压", "折弯", "激光切割", "线切割", "磨床",
    "铆件", "车床", "铓床", "钻床", "打磨", "冲孔",
    "调试", "维修", "安装", "装配", "检验", "清洗", "打包",
)

_IGNORE_WORDS = (
    "调试", "压伤", "报废", "返工", "不良", "废品", "次品", "返修",
    "试压", "打压", "探伤", "工伤", "待检", "检验中",
)

_MODEL_RE = re.compile(
    r'(?:型号\s*[:：]?\s*)?'
    r'([A-Za-z]{0,4}\d{4,12}[A-Za-z]{0,3})')

_QTY_RE = re.compile(r'(\d{1,7})\s*(?:件|个|只|块|套|pcs|PCS)')

_DUTY_RE = re.compile(r'(?:出勤|上班|上工|工作)\s*(\d{1,2}(?:\.\d+)?)\s*小?时')

_SPAN_RE = re.compile(
    r'(\d{1,2}):(\d{2})\s*[-~至]\s*(\d{1,2}):(\d{2})')


def parse_date_token(text: str) -> str | None:
    """识别日期，返回 'YYYY-MM-DD' 或 None。"""
    m = re.search(r'(\d{4})\s*[年./-]\s*(\d{1,2})\s*[月./-]\s*(\d{1,2})日?', text)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            q = date(y, mo, d)
            return q.isoformat()
        except ValueError:
            return None
    m = re.search(r'(\d{1,2})\s*月\s*(\d{1,2})\s*[日号]', text)
    if m:
        today = date.today()
        try:
            q = date(today.year, int(m.group(1)), int(m.group(2)))
            return q.isoformat()
        except ValueError:
            return None
    m = re.search(r'(\d{1,2})\s*[日号]', text)
    if m:
        today = date.today()
        try:
            q = date(today.year, today.month, int(m.group(1)))
            return q.isoformat()
        except ValueError:
            return None
    if '昨天' in text:
        d = date.today()
        return d.isoformat()
    if '今天' in text:
        return date.today().isoformat()
    return None


def _match_work_type(text: str) -> str:
    for t in sorted(WORK_TYPES, key=len, reverse=True):
        if t in text:
            return t.replace("打样", "") or ""
    return ''


def _split_record_line(ln: str):
    segs = [x.strip() for x in re.split(r'[,，、;；]', ln) if x.strip()]
    out = []
    last_model = ''
    for seg in segs:
        if any(w in seg for w in _IGNORE_WORDS):
            continue
        mm = _MODEL_RE.search(seg)
        model = mm.group(1) if mm else last_model
        if mm:
            last_model = model
        mq = _QTY_RE.search(seg)
        if mq is None:
            mq = re.search(r'(?:共|计)\s*(\d{1,7})(?!\d)', seg)
        if mq is None:
            continue
        qty = int(mq.group(1))
        wt = _match_work_type(seg)
        if not model and not wt:
            continue
        out.append({'part_model': model, 'work_type': wt, 'quantity': qty})
    return out


def parse_attendance_text(text: str) -> dict:
    """多行考勤文字 → {date, work_hours, records:[...]}
    records 每项: {part_model, work_type, quantity}。"""
    raw = (text or '').strip()
    out = {'date': None, 'work_hours': None, 'records': [], 'notes': []}
    if not raw:
        out['notes'].append('输入为空')
        return out

    # 日期
    for ln in raw.splitlines():
        d = parse_date_token(ln)
        if d:
            out['date'] = d
            break

    # 工时：优先"出勤X小时"，其次时间区间
    wh = None
    for ln in raw.splitlines():
        m = _DUTY_RE.search(ln)
        if m:
            wh = round(min(24.0, max(0.0, float(m.group(1)))), 1)
            break
    if wh is None:
        for ln in raw.splitlines():
            m = _SPAN_RE.search(ln)
            if m:
                h1, m1, h2, m2 = (int(m.group(1)), int(m.group(2)),
                                  int(m.group(3)), int(m.group(4)))
                mins = (h2 * 60 + m2) - (h1 * 60 + m1)
                if mins > 0:
                    wh = round(min(24.0, max(0.0, mins / 60.0)), 1)
                break
    out['work_hours'] = wh

    # 记录（不因日期行而跳过同一行，日期已在上面提取）
    for ln in raw.splitlines():
        t = ln.strip()
        if not t:
            continue
        if _MODEL_RE.search(t) is None and _QTY_RE.search(t) is None:
            continue
        recs = _split_record_line(t)
        for r in recs:
            out['records'].append(r)

    if not out['records']:
        out['notes'].append('没认出记录行。每行写"型号+类型+数量"，如：\n10800061冷铆1650件')
    elif out['date'] is None:
        out['notes'].append('没认出日期，保存前请核对日期')
    return out


# ---------------------------------------------------------------------------
# 加班计算
# ---------------------------------------------------------------------------
def calc_overtime(shift_type: str, work_hours: float, end_time_str: str) -> float:
    """
    计算加班时长。
    白班：max(0, work_hours - 8)
    夜班：max(0, 下班时刻 - 4:00)，最大 8h
    """
    if shift_type == "night":
        if not end_time_str:
            return 0.0
        try:
            parts = end_time_str.split(":")
            h = int(parts[0])
            m = int(parts[1]) if len(parts) > 1 else 0
            if h < 4:  # 次日凌晨，如 02:00 → 算作 h+24
                h += 24
            ot = h - 4 + m / 60.0
            return max(0.0, min(8.0, ot))
        except Exception:
            return 0.0
    else:
        return max(0.0, work_hours - 8.0)


def default_shift_times(shift_type: str):
    """返回 (start_time, end_time, work_hours)"""
    if shift_type == "night":
        return "20:00", "04:00", 8.0
    else:
        return "08:00", "17:00", 8.0


def night_record_date(record_date_str: str, shift_type: str) -> str:
    """
    夜班：实际起班日 → 归属日期 -1 天
    例如：用户在界面选 9月5日（夜班）→ 存库日期为 9月4日
    """
    if shift_type != "night":
        return record_date_str
    from datetime import datetime, timedelta
    try:
        d = datetime.strptime(record_date_str, "%Y-%m-%d").date() - timedelta(days=1)
        return d.isoformat()
    except Exception:
        return record_date_str
