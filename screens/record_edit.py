# -*- coding: utf-8 -*-
"""新增/编辑记录 — 全屏页面（Python 动态构建表单）"""
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP

from kivy.app import App
from kivy.properties import (
    ObjectProperty, StringProperty, BooleanProperty, ListProperty
)
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput

from kivymd.uix.button import MDIconButton, MDRaisedButton, MDFlatButton
from kivymd.uix.chip import MDChip
from kivymd.uix.dialog import MDDialog
from kivymd.uix.label import MDLabel
from kivymd.uix.screen import MDScreen
from kivymd.uix.textfield import MDTextField
from kivymd.uix.card import MDCard
from kivymd.uix.snackbar import Snackbar

from db import (
    Database, calc_wage_fen, calc_hourly_wage_fen,
    wage_text, fmt_hours, price_text
)
from business import (
    parse_attendance_text, calc_overtime,
    default_shift_times, night_record_date
)


# ---------------------------------------------------------------------------
# 辅助：标准高度 TextField
# ---------------------------------------------------------------------------
def tf(hint, text="", multiline=False, input_filter=None, readonly=False):
    t = MDTextField(
        hint_text=hint,
        text=text,
        multiline=multiline,
        readonly=readonly,
        size_hint_y=None,
        height="48dp",
    )
    if input_filter:
        t.input_filter = input_filter
    return t


# ---------------------------------------------------------------------------
# 明细行卡片（Python 构建）
# ---------------------------------------------------------------------------
class ItemCard(BoxLayout):
    """一条明细行：计费方式 / 型号 / 类型 / 数量 / 单价 / 金额"""
    idx = 0
    screen = None  # RecordEditScreen ref

    def __init__(self, idx, screen, item, **kwargs):
        super().__init__(**kwargs)
        self.idx = idx
        self.screen = screen
        self.item = item
        self.orientation = "vertical"
        self.size_hint_y = None
        self.height = "200dp"
        self.padding = "8dp"
        self.spacing = "4dp"

        self.charge_chip = None
        self.mode = item.get("charge_mode", 0)

        self._build()

    def _build(self):
        self.clear_widgets()

        # 顶部栏：计费方式 + 删除按钮
        top = BoxLayout(size_hint_y=None, height="36dp", spacing="8dp")

        def chip(text, is_active, on_func):
            c = MDChip(
                text=text,
                size_hint_x=0.5,
                size_hint_y=None,
                height="32dp",
                md_bg_color=(
                    "#FF9800" if is_active else "#E0E0E0"
                ),
                text_color=(
                    (1, 1, 1, 1) if is_active else (0.4, 0.4, 0.4, 1)
                ),
            )
            c.bind(on_active=on_func)
            return c

        self.charge_chip = chip(
            "计件",
            self.mode == 0,
            lambda *a: self._set_mode(0),
        )
        time_chip = chip(
            "计时",
            self.mode == 1,
            lambda *a: self._set_mode(1),
        )
        del_btn = MDIconButton(
            icon="close", size_hint=(None, None), size=("36dp", "36dp"),
            pos_hint={"right": 1},
            on_release=lambda *a: self.screen._remove_item(self.idx),
        )
        top.add_widget(self.charge_chip)
        top.add_widget(time_chip)
        top.add_widget(del_btn)
        self.add_widget(top)

        # 计件行
        self.piece_grid = GridLayout(cols=3, spacing="6dp", size_hint_y=None, height="96dp")
        self.model_tf = tf("型号", self.item.get("part_model", ""))
        self.model_tf.bind(on_text_validate=lambda *a: self._on_model_change())
        self.type_tf = tf("类型", self.item.get("work_type", ""))
        self.qty_tf = tf("数量（件）", self.item.get("quantity", ""), input_filter="int")
        self.price_tf = tf("单价（元/件）", self.item.get("price_display", "—"), input_filter="float")
        self.piece_grid.add_widget(self.model_tf)
        self.piece_grid.add_widget(self.type_tf)
        self.piece_grid.add_widget(self.qty_tf)
        self.add_widget(self.piece_grid)

        # 计时行
        self.time_grid = GridLayout(cols=2, spacing="6dp", size_hint_y=None, height="64dp")
        self.hours_tf = tf("计费小时", self.item.get("charge_hours", ""), input_filter="float")
        self.hourly_tf = tf("时薪（元/h）", self.item.get("price_display", "—"), input_filter="float")
        self.time_grid.add_widget(self.hours_tf)
        self.time_grid.add_widget(self.hourly_tf)
        self.add_widget(self.time_grid)

        # 金额
        self.wage_lbl = Label(
            text=(self.item.get("wage_display", "0.00") + " 元"),
            font_size="16sp", bold=True,
            color=(0.086, 0.467, 1.0, 1.0),
            size_hint_y=None, height="28dp",
            halign="right", valign="middle",
        )
        self.add_widget(self.wage_lbl)

        self._sync_mode()

        # 绑定变更事件
        for w in [self.model_tf, self.type_tf, self.qty_tf, self.price_tf,
                  self.hours_tf, self.hourly_tf]:
            w.bind(text=lambda *a: self._recalc())

    def _sync_mode(self):
        piece_vis = self.mode == 0
        self.piece_grid.opacity = 1 if piece_vis else 0
        self.piece_grid.height = "96dp" if piece_vis else 0
        self.time_grid.opacity = 1 if not piece_vis else 0
        self.time_grid.height = "64dp" if not piece_vis else 0

    def _set_mode(self, mode):
        if self.mode == mode:
            return
        self.mode = mode
        self.item["charge_mode"] = mode
        self._sync_mode()
        self._recalc()

    def _on_model_change(self):
        name = self.model_tf.text.strip()
        self.item["part_model"] = name
        if not name:
            return
        app = App.get_running_app()
        db = getattr(app, 'db', None)
        if not db:
            return
        model = db.model_by_name(name)
        if model:
            if self.mode == 0:
                p = price_text(model.get("piece_milli") or 0)
            else:
                p = price_text(model.get("hourly_milli") or 0)
            self.price_tf.text = p
            self.item["price_display"] = p
        self._recalc()

    def _recalc(self, *args):
        try:
            if self.mode == 0:
                qty = int(self.qty_tf.text or "0")
                price = int(float(self.price_tf.text or "0") * 1000)
                fen = calc_wage_fen(qty, price)
            else:
                hrs = float(self.hours_tf.text or "0")
                price = int(float(self.hourly_tf.text or "0") * 1000)
                fen = calc_hourly_wage_fen(hrs, price)
            self.wage_lbl.text = ("%0.2f" % (fen / 100.0)) + " 元"
            self.item["wage_display"] = "%0.2f" % (fen / 100.0)
            self.item["quantity"] = self.qty_tf.text
            self.item["charge_hours"] = self.hours_tf.text
            self.item["work_type"] = self.type_tf.text
            self.item["price_display"] = self.price_tf.text if self.mode == 0 else self.hourly_tf.text
        except Exception:
            self.wage_lbl.text = "0.00 元"


# ---------------------------------------------------------------------------
# 记录编辑页面
# ---------------------------------------------------------------------------
class RecordEditScreen(MDScreen):
    db: Database = None
    editing_id = None
    shift_type = "day"
    record_date = ""
    work_hours = "8.0"
    master_hours = "0.0"
    overtime_hours = "0.0"
    start_time = "08:00"
    end_time = "17:00"
    smart_text = ""
    items = []
    item_cards = []

    def on_enter(self):
        app = self.manager.parent.parent
        self.db = getattr(app, 'db', None)
        if not self.db:
            return

        today = date.today().isoformat()
        self.record_date = today
        self._set_shift_defaults()
        self.items = [self._make_item()]
        self._build_form()

    def _set_shift_defaults(self):
        st, et, wh = default_shift_times(self.shift_type)
        self.start_time = st
        self.end_time = et
        self.work_hours = fmt_hours(wh)
        self.master_hours = "0.0"
        self.overtime_hours = "0.0"

    def _build_form(self):
        """清空并重建表单"""
        content = self.ids.get("form_content")
        if content is None:
            return
        content.clear_widgets()
        self.item_cards.clear()

        # 班别
        shift_row = BoxLayout(size_hint_y=None, height="40dp", spacing="8dp")
        day_chip = MDChip(text="白班", size_hint_x=0.5, height="36dp",
                          md_bg_color=("#1976D2" if self.shift_type == "day" else "#E0E0E0"),
                          text_color=(1, 1, 1, 1) if self.shift_type == "day" else (0.4, 0.4, 0.4, 1))
        day_chip.bind(on_active=lambda *a: self._set_shift("day"))
        night_chip = MDChip(text="夜班", size_hint_x=0.5, height="36dp",
                            md_bg_color=("#1565C0" if self.shift_type == "night" else "#E0E0E0"),
                            text_color=(1, 1, 1, 1) if self.shift_type == "night" else (0.4, 0.4, 0.4, 1))
        night_chip.bind(on_active=lambda *a: self._set_shift("night"))
        shift_row.add_widget(day_chip)
        shift_row.add_widget(night_chip)
        content.add_widget(shift_row)
        content.add_widget(self._divider())

        # 日期 & 时间
        row1 = GridLayout(cols=2, spacing="8dp", size_hint_y=None, height="104dp")
        self.date_tf = tf("日期（如 2026-09-09）", self.record_date)
        self.date_tf.bind(text=lambda *a: setattr(self, 'record_date', self.date_tf.text))
        self.start_tf = tf("开始时间（如 08:00）", self.start_time)
        self.start_tf.bind(text=lambda *a: setattr(self, 'start_time', self.start_tf.text))
        self.end_tf = tf("结束时间（如 17:00）", self.end_time)
        self.end_tf.bind(text=lambda *a: self.recalc_overtime())
        self.work_tf = tf("出勤时长（h）", self.work_hours, input_filter="float")
        self.work_tf.bind(text=lambda *a: self.recalc_overtime())
        self.master_tf = tf("大工时长（h）", self.master_hours, input_filter="float")
        self.master_tf.bind(text=lambda *a: setattr(self, 'master_hours', self.master_tf.text))
        self.ot_tf = tf("加班时长（h，自动算）", self.overtime_hours, readonly=True)
        row1.add_widget(self.date_tf)
        row1.add_widget(self.start_tf)
        row1.add_widget(self.end_tf)
        row1.add_widget(self.work_tf)
        row1.add_widget(self.master_tf)
        row1.add_widget(self.ot_tf)
        content.add_widget(row1)
        content.add_widget(self._divider())

        # 智能输入
        smart_lbl = Label(text="智能输入（可选）", font_size="12sp", color=(0.5, 0.5, 0.5, 1),
                          size_hint_y=None, height="20dp", halign="left")
        content.add_widget(smart_lbl)
        self.smart_tf = MDTextField(
            hint_text="粘贴考勤文字，如：\n9月9日 冷铆 10800061 1650件，焊接 10800034 200件",
            multiline=True, size_hint_y=None, height="100dp",
        )
        content.add_widget(self.smart_tf)
        parse_btn = MDRaisedButton(text="智能解析", icon="auto-fix", size_hint_y=None, height="40dp",
                                   on_release=lambda *a: self.run_parse())
        content.add_widget(parse_btn)
        content.add_widget(self._divider())

        # 明细区
        items_lbl = Label(text="明细记录", font_size="12sp", color=(0.5, 0.5, 0.5, 1),
                          size_hint_y=None, height="20dp")
        content.add_widget(items_lbl)
        self.items_container = BoxLayout(orientation="vertical", spacing="8dp",
                                          size_hint_y=None, height=0)
        content.add_widget(self.items_container)
        self._rebuild_item_cards()

        add_btn = MDRaisedButton(text="+ 添加明细", icon="plus", size_hint_y=None, height="44dp",
                                 md_bg_color=(0.3, 0.7, 0.3, 1),
                                 on_release=lambda *a: self.add_item())
        content.add_widget(add_btn)

    def _divider(self):
        return Label(size_hint_y=None, height="1dp", size_hint_x=1,
                     canvas_after=None)

    def _set_shift(self, stype):
        self.shift_type = stype
        self._set_shift_defaults()
        self._build_form()

    def recalc_overtime(self):
        try:
            wh = float(self.work_tf.text or "0")
            et = self.end_tf.text or ""
            ot = calc_overtime(self.shift_type, wh, et)
            self.ot_tf.text = fmt_hours(ot)
            self.overtime_hours = self.ot_tf.text
        except Exception:
            pass

    def run_parse(self):
        text = self.smart_tf.text or ""
        if not text.strip():
            return
        result = parse_attendance_text(text)
        recs = result.get("records", [])

        if not recs:
            Snackbar(text="未识别到记录，请检查格式").open()
            return

        if result.get("date"):
            self.date_tf.text = result["date"]
            self.record_date = result["date"]
        if result.get("work_hours"):
            wh = fmt_hours(result["work_hours"])
            self.work_tf.text = wh
            self.work_hours = wh
            self.recalc_overtime()

        # 确认预览
        preview_text = "\n".join(
            f"· {r.get('part_model','')} {r.get('work_type','')} {r.get('quantity',0)}件"
            for r in recs
        )
        dialog = MDDialog(
            title=f"识别到 {len(recs)} 条记录：",
            text=preview_text,
            buttons=[
                MDFlatButton(text="取消", on_release=lambda x: dialog.dismiss()),
                MDRaisedButton(text="填入", on_release=lambda x: self._apply_parse(recs, dialog)),
            ],
        )
        dialog.open()

    def _apply_parse(self, recs, dialog):
        dialog.dismiss()
        # 替换现有空行
        for i, r in enumerate(recs):
            item = self._make_item()
            item["part_model"] = r.get("part_model", "")
            item["work_type"] = r.get("work_type", "")
            item["quantity"] = str(r.get("quantity", 0))
            model = self.db.model_by_name(item["part_model"])
            if model:
                item["price_display"] = price_text(model.get("piece_milli") or 0)
            self.items.append(item)

        # 去掉初始空行
        if self.items and not self.items[0]["part_model"]:
            self.items.pop(0)

        self._rebuild_item_cards()

    def add_item(self):
        self.items.append(self._make_item())
        self._rebuild_item_cards()

    def _remove_item(self, idx):
        if len(self.items) > 1:
            self.items.pop(idx)
            self._rebuild_item_cards()

    def _rebuild_item_cards(self):
        self.item_cards.clear()
        if hasattr(self, 'items_container') and self.items_container:
            self.items_container.clear_widgets()
            for i, item in enumerate(self.items):
                card = ItemCard(i, self, item)
                self.item_cards.append(card)
                self.items_container.add_widget(card)
            self.items_container.height = len(self.items) * 216

    def _make_item(self):
        return {
            "work_type": "",
            "part_model": "",
            "quantity": "",
            "charge_mode": 0,
            "charge_hours": "",
            "price_display": "—",
            "wage_display": "0.00",
        }

    def save(self):
        if not self.record_date:
            Snackbar(text="请选择日期").open()
            return

        valid = [it for it in self.items if it.get("part_model", "").strip()]
        if not valid:
            Snackbar(text="请至少填写一条明细").open()
            return

        try:
            work_h = float(self.work_tf.text or 0)
            master_h = float(self.master_tf.text or 0)
            overtime_h = float(self.ot_tf.text or 0)
        except Exception:
            Snackbar(text="工时格式错误").open()
            return

        saved_date = night_record_date(self.record_date, self.shift_type)

        for item in valid:
            mode = item.get("charge_mode", 0)
            model_name = item.get("part_model", "").strip()
            try:
                if mode == 0:
                    qty = int(item.get("quantity") or 0)
                    price_milli = int(float(item.get("price_display") or "0") * 1000)
                    wage_fen = calc_wage_fen(qty, price_milli)
                    charge_hours = 0.0
                else:
                    charge_hours = float(item.get("charge_hours") or 0)
                    price_milli = int(float(item.get("price_display") or "0") * 1000)
                    wage_fen = calc_hourly_wage_fen(charge_hours, price_milli)
                    qty = 0
            except Exception:
                wage_fen = 0
                price_milli = 0
                qty = 0
                charge_hours = 0.0

            if self.editing_id:
                self.db.update_record(
                    self.editing_id,
                    saved_date, self.shift_type,
                    self.start_tf.text, self.end_tf.text,
                    work_h, master_h, overtime_h,
                    item.get("work_type", ""), model_name,
                    qty, price_milli, wage_fen, 0, mode, charge_hours,
                )
            else:
                self.db.add_record(
                    saved_date, self.shift_type,
                    self.start_tf.text, self.end_tf.text,
                    work_h, master_h, overtime_h,
                    item.get("work_type", ""), model_name,
                    qty, price_milli, wage_fen, 0, mode, charge_hours,
                )

        Snackbar(text="保存成功").open()
        self.manager.current = "shell"

    def go_back(self):
        self.manager.current = "shell"
