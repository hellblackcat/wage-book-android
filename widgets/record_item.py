# -*- coding: utf-8 -*-
"""记录卡片组件"""
from kivy.properties import DictProperty, StringProperty
from kivymd.uix.behaviors import RectangularRippleBehavior
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.chip import MDChip


class RecordItem(MDBoxLayout):
    """KV 中 viewclass='RecordItem' 对应的 widget"""
    record = DictProperty()
    wage_display = StringProperty("0.00")
    shift_display = StringProperty("白班")

    def open_edit(self):
        # 通过 shell → records screen → open_add_dialog
        from kivymd.app import MDApp
        app = MDApp.get_running_app()
        # 找到 records screen
        for scr in app.root.get_screen("shell").walk(restrict=True):
            if hasattr(scr, 'open_add_dialog'):
                scr.open_add_dialog(self.record.get("id"))
                break

    def open_delete_confirm(self):
        from kivymd.app import MDApp
        from kivymd.uix.dialog import MDDialog
        from kivymd.uix.button import MDFlatButton, MDRaisedButton

        app = MDApp.get_running_app()
        db = getattr(app, 'db', None)
        if not db:
            return

        def confirm(*args):
            db.delete_record(self.record.get("id"))
            dialog.dismiss()
            # 刷新列表
            for scr in app.root.get_screen("shell").walk(restrict=True):
                if hasattr(scr, 'load_records'):
                    scr.load_records()

        dialog = MDDialog(
            title="确认删除",
            text="确定删除这条记录吗？",
            buttons=[
                MDFlatButton(text="取消", on_release=lambda x: dialog.dismiss()),
                MDRaisedButton(text="删除", on_release=confirm),
            ],
        )
        dialog.open()
