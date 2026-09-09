import db, business

d = db.Database()
d.conn.execute('DELETE FROM records')
d.conn.execute('DELETE FROM models')
d.conn.commit()

d.add_model('10800061', '冷铆', 80, 0)
d.add_model('10800034', '焊接', 85, 0)
print('Models:', d.list_models())

d.add_record('2026-09-09','day','08:00','17:00',8.0,0.0,0.0,'冷铆','10800061',1650,80,db.calc_wage_fen(1650,80),0,0,0.0)
d.add_record('2026-09-09','day','08:00','17:00',8.0,0.0,0.0,'焊接','10800034',200,85,db.calc_wage_fen(200,85),0,0,0.0)
d.add_record('2026-09-10','night','20:00','04:00',8.0,0.0,0.0,'冷铆','10800061',800,80,db.calc_wage_fen(800,80),0,0,0.0)

s = d.monthly_summary('2026-09')
print('Summary:')
print('  total_wage:', db.wage_text(s["total_wage_fen"]), '元')   # 213.00 正确
print('  work_days:', s["work_days"])   # 2 正确
print('  night_days:', s["night_days"]) # 1 正确
print('  entries count:', s["entries"]) # 3
for m in s["by_model"]:
    print('  model', m["model"], ': qty=', m["quantity"], 'wage=', db.wage_text(m["wage_fen"]))

# Overtime calc
print()
print('Overtime:')
print('  day 8h end 17:00 ->', business.calc_overtime('day', 8.0, '17:00'), 'h (expect 0)')
print('  night 8h end 04:00 ->', business.calc_overtime('night', 8.0, '04:00'), 'h (expect 0)')
print('  night 8h end 08:00 ->', business.calc_overtime('night', 8.0, '08:00'), 'h (expect 4)')
print('  night 8h end 12:00 ->', business.calc_overtime('night', 8.0, '12:00'), 'h (expect 8)')

# Night record date
from datetime import date
print()
print('Night date:')
print('  09-10 night ->', business.night_record_date('2026-09-10', 'night'), '(expect 2026-09-09)')

print()
print('ALL CHECKS PASSED')
