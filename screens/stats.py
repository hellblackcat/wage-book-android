# -*- coding: utf-8 -*-
"""统计 Tab"""
from datetime import date
from kivy.properties import ObjectProperty, StringProperty, ListProperty
from kivymd.uix.screen import MDScreen


class StatsScreen(MDScreen):
    db: ObjectProperty()
    current_month = StringProperty()
    summary_data = ObjectProperty()
    model_list = ListProperty()

    def on_enter(self):
        app = self.manager.parent.parent
        self.db = getattr(app, 'db', None)
        if self.db:
            self.current_month = date.today().strftime("%Y-%m")
            self.load_stats()

    def prev_month(self):
        y, m = map(int, self.current_month.split("-"))
        m -= 1
        if m < 1:
            m, y = 12, y - 1
        self.current_month = f"{y:04d}-{m:02d}"
        self.load_stats()

    def next_month(self):
        y, m = map(int, self.current_month.split("-"))
        m += 1
        if m > 12:
            m, y = 1, y + 1
        self.current_month = f"{y:04d}-{m:02d}"
        self.load_stats()

    def load_stats(self):
        if not self.db:
            return
        s = self.db.monthly_summary(self.current_month)
        self.summary_data = s
        self.model_list = sorted(s.get("by_model", []), key=lambda x: x["wage_fen"], reverse=True)

    def wage_display(self, fen: int) -> str:
        return "%0.2f" % (fen / 100.0)

    def fmt_hours(self, v) -> str:
        return "%0.1f" % float(v or 0)
