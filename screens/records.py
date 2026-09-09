# -*- coding: utf-8 -*-
"""记录 Tab"""
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

from kivy.properties import ObjectProperty, StringProperty, ListProperty, BooleanProperty
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDFlatButton, MDRaisedButton
from kivymd.uix.dialog import MDDialog
from kivymd.uix.label import MDLabel
from kivymd.uix.screen import MDScreen
from kivymd.uix.textfield import MDTextField

from db import Database, wage_text, fmt_hours, calc_wage_fen, calc_hourly_wage_fen
from business import (
    parse_attendance_text, calc_overtime, default_shift_times, night_record_date
)


class RecordsScreen(MDScreen):
    db: Database = ObjectProperty()
    current_month = StringProperty()
    records_list = ListProperty()
    _dialog = None
    _add_dialog = None

    def on_enter(self):
        self.db = self.app = self.manager.parent.parent
        if hasattr(self.app, 'db'):
            self.db = self.app.db
        self.current_month = date.today().strftime("%Y-%m")
        self.load_records()

    def on_leave(self):
        pass

    def load_records(self, month=None):
        if month:
            self.current_month = month
        elif self.current_month:
            month = self.current_month
        else:
            month = date.today().strftime("%Y-%m")

        recs = self.db.list_records(month)
        self.records_list = recs

    def prev_month(self):
        y, m = map(int, self.current_month.split("-"))
        m -= 1
        if m < 1:
            m, y = 12, y - 1
        self.current_month = f"{y:04d}-{m:02d}"
        self.load_records()

    def next_month(self):
        y, m = map(int, self.current_month.split("-"))
        m += 1
        if m > 12:
            m, y = 1, y + 1
        self.current_month = f"{y:04d}-{m:02d}"
        self.load_records()

    def open_add_dialog(self, record_id=None):
        # 找到 ShellScreen → 导航到 record_edit
        root = self.manager
        edit_scr = root.get_screen("record_edit")
        if record_id:
            rec = self.db.get_record(record_id)
            edit_scr.editing_id = record_id
        else:
            edit_scr.editing_id = None
        root.current = "record_edit"

    def delete_record(self, record_id):
        def confirm(*args):
            self.db.delete_record(record_id)
            self.load_records()
            self._confirm_dialog.dismiss()

        self._confirm_dialog = MDDialog(
            title="确认删除",
            text="确定删除这条记录吗？",
            buttons=[
                MDFlatButton(text="取消", on_release=lambda x: self._confirm_dialog.dismiss()),
                MDRaisedButton(text="删除", on_release=confirm),
            ],
        )
        self._confirm_dialog.open()

    # ------------------------------------------------------------------
    # 新增/编辑记录弹窗
    # ------------------------------------------------------------------
    def _show_record_dialog(self, record=None):
        from kivymd.uix.screen import MDScreen as MDScr
        # 弹窗用独立 Screen 实现，全屏覆盖
        class RecordEditScreen(MDScr):
            parent_app = ObjectProperty()

        edit = RecordEditScreen(name="record_edit")
        edit.parent_app = self.app
        self.manager.add_widget(edit)
        self.manager.current = "record_edit"

    def close_edit(self):
        self.manager.remove_widget(self.manager.get_screen("record_edit"))
        self.manager.current = "records"
        self.load_records()
