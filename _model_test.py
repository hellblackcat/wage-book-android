import re, sys
sys.path.insert(0, '.')

import business

# 直接测 parse_attendance_text 的每一行过滤逻辑
raw = '9月9日 冷铆 10800061 1650件'
_MODEL_RE = re.compile(
    r'(?:型号\s*[:：]?\s*)?'
    r'([A-Za-z]{0,4}\d{4,12}[A-Za-z]{0,3})')
_QTY_RE = re.compile(r'(\d{1,7})\s*(?:件|个|只|块|套|pcs|PCS)')
_DUTY_RE = re.compile(r'(?:出勤|上班|上工|工作)\s*(\d{1,2}(?:\.\d+)?)\s*小?时')
_SPAN_RE = re.compile(r'(\d{1,2}):(\d{2})\s*[-~至]\s*(\d{1,2}):(\d{2})')

print(f'Input: {repr(raw)}')
print(f'parse_date_token result: {business.parse_date_token(raw)}')
print(f'_DUTY_RE.search: {_DUTY_RE.search(raw)}')
print(f'_SPAN_RE.search: {_SPAN_RE.search(raw)}')
print(f'_MODEL_RE.search: {_MODEL_RE.search(raw)}')
print(f'_QTY_RE.search: {_QTY_RE.search(raw)}')
print()
print(f'Filter condition: model={_MODEL_RE.search(raw)} qty={_QTY_RE.search(raw)}')
print(f'Should skip: {_MODEL_RE.search(raw) is None and _QTY_RE.search(raw) is None}')

# Now call parse with a clean string without date prefix
print()
print('Without date prefix:')
r = business.parse_attendance_text('冷铆 10800061 1650件')
print(f'Result: {r}')
