import sys
sys.path.insert(0, '.')
print('db...')
try:
    import db
    print('db ok')
except Exception as e:
    print('db error:', e)

print('business...')
try:
    import business
    r = business.parse_attendance_text('9月9日 冷铆 10800061 1650件')
    print('parse:', r)
except Exception as e:
    print('business error:', e)

print('done')
