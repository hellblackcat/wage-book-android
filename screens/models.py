# -*- coding: utf-8 -*-
"""型号管理 Tab"""
from kivy.properties import ObjectProperty, ListProperty
from kivymd.uix.screen import MDScreen
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton, MDRaisedButton
from kivymd.uix.textfield import MDTextField


class ModelsScreen(MDScreen):
    db: ObjectProperty()
    models_list = ListProperty()
    _dialog = None

    def on_enter(self):
        app = self.manager.parent.parent
        self.db = getattr(app, 'db', None)
        self.load_models()

    def load_models(self):
        if self.db:
            self.models_list = self.db.list_models()

    def open_add_dialog(self):
        self._show_model_dialog()

    def open_edit_dialog(self, model_id):
        if self.db:
            m = self.db.model_by_id(model_id)
            if m:
                self._show_model_dialog(model=m)

    def _show_model_dialog(self, model=None):
        is_edit = model is not None

        name_field = MDTextField(
            hint_text="型号名称",
            text=model.get("name", "") if model else "",
            disabled=is_edit,
            size_hint_x=1,
        )
        type_field = MDTextField(
            hint_text="默认类型（如：冷铆）",
            text=model.get("default_type", "") if model else "",
            size_hint_x=1,
        )
        piece_field = MDTextField(
            hint_text="计件单价（元/件）",
            text=str((model.get("piece_milli") or 0) / 1000) if model else "",
            input_filter="float",
            size_hint_x=1,
        )
        hourly_field = MDTextField(
            hint_text="计时单价（元/小时）",
            text=str((model.get("hourly_milli") or 0) / 1000) if model else "",
            input_filter="float",
            size_hint_x=1,
        )

        def save(*args):
            name = name_field.text.strip()
            if not name:
                name_field.error = True
                return

            def_type = type_field.text.strip()
            piece_milli = int(float(piece_field.text or "0") * 1000)
            hourly_milli = int(float(hourly_field.text or "0") * 1000)

            if is_edit:
                self.db.update_model(
                    model["id"], name, def_type,
                    piece_milli, hourly_milli, sync_history=True)
            else:
                try:
                    self.db.add_model(name, def_type, piece_milli, hourly_milli)
                except Exception as e:
                    if "UNIQUE constraint" in str(e):
                        name_field.error = True
                        name_field.helper_text = "型号已存在"
                        return

            self._dialog.dismiss()
            self.load_models()

        buttons = [
            MDFlatButton(text="取消", on_release=lambda x: self._dialog.dismiss()),
            MDRaisedButton(text="保存", on_release=save),
        ]
        title = "编辑型号" if is_edit else "新增型号"
        self._dialog = MDDialog(title=title, items=[name_field, type_field, piece_field, hourly_field], buttons=buttons)
        self._dialog.open()
