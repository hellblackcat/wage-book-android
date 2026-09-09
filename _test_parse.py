import business

tests = [
    '10800061冷铆1650件',
    '9月9日 冷铆 10800061 1650件，出勤8小时',
    '昨天 m02071897焊接打样332件',
    '8月30日 10800061 冷铆 500件,10800034 焊接 200件',
    '压伤15件',
]
for t in tests:
    r = business.parse_attendance_text(t)
    print(f'Input: {t}')
    print(f'  -> date={r["date"]} work_h={r["work_hours"]} records={r["records"]}')
    print()
