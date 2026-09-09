# -*- coding: utf-8 -*-
"""首次设置姓名"""
from kivy.app import App
from kivymd.uix.screen import MDScreen
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.label import MDLabel


class SetupScreen(MDScreen):
    def save_name(self):
        name = self.ids.name_field.text.strip()
        if not name:
            self.ids.name_field.error = True
            self.ids.name_field.helper_text = "请输入您的姓名"
            return

        app = App.get_running_app()
        app.db.set_user_name(name)

        # 跳到主界面
        # 找到 shell 并切换
        for scr in self.manager.screens:
            if scr.name == "shell":
                self.manager.current = "shell"
                break
