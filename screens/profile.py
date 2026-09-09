# -*- coding: utf-8 -*-
"""我的 Tab"""
from kivy.properties import ObjectProperty, StringProperty
from kivymd.uix.screen import MDScreen
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton, MDRaisedButton
from kivymd.uix.textfield import MDTextField


class ProfileScreen(MDScreen):
    db: ObjectProperty()
    user_name = StringProperty("")

    def on_enter(self):
        app = self.manager.parent.parent
        self.db = getattr(app, 'db', None)
        if self.db:
            user = self.db.get_user()
            self.user_name = user.get("name", "") if user else ""

    def edit_name(self):
        field = MDTextField(
            hint_text="请输入姓名",
            text=self.user_name,
            size_hint_x=1,
        )

        def save(*args):
            name = field.text.strip()
            if name:
                self.db.set_user_name(name)
                self.user_name = name
            self._dialog.dismiss()

        self._dialog = MDDialog(
            title="修改姓名",
            items=[field],
            buttons=[
                MDFlatButton(text="取消", on_release=lambda x: self._dialog.dismiss()),
                MDRaisedButton(text="保存", on_release=save),
            ],
        )
        self._dialog.open()
