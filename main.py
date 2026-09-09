# -*- coding: utf-8 -*-
"""
工资记账表 — 安卓版
入口文件
"""
import os
import sys

# 解决打包后路径问题
if getattr(sys, 'frozen', False):
    os.chdir(sys._MEIPASS)

from kivy.app import App
from kivy.core.text import LabelBase
from kivy.lang import Builder
from kivy.resources import resource_add_path
from kivymd.app import MDApp
from kivymd.theming import ThemeManager

# 预加载所有 kv 文件
_kv_dir = os.path.join(os.path.dirname(__file__), "screens")
_widgets_dir = os.path.join(os.path.dirname(__file__), "widgets")
for _d in [_kv_dir, _widgets_dir]:
    if os.path.isdir(_d):
        for _f in os.listdir(_d):
            if _f.endswith(".kv"):
                Builder.load_file(os.path.join(_d, _f))


class WageBookApp(MDApp):
    title = "工资记账表"

    def on_start(self):
        from db import Database
        self.db = Database()

        # 检查用户名
        user = self.db.get_user()
        if not user or not user.get("name", "").strip():
            self.root.current = "setup"
        else:
            self.root.current = "shell"

    def build(self):
        self.theme_cls.theme_style = "Light"
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.primary_hue = "700"
        self.theme_cls.material_style = "M3"

        # 中文字体（Android 兼容性）
        font_dir = os.path.join(os.path.dirname(__file__), "fonts")
        if os.path.isdir(font_dir):
            resource_add_path(font_dir)
            for f in os.listdir(font_dir):
                if f.endswith(".ttf"):
                    try:
                        LabelBase.register(name="CN", fn_regular=os.path.join(font_dir, f))
                    except Exception:
                        pass

        # 加载主 kv
        Builder.load_file(os.path.join(os.path.dirname(__file__), "main.kv"))

        # 导入所有屏幕
        import screens.shell
        import screens.records
        import screens.stats
        import screens.models
        import screens.profile
        import screens.record_edit
        import screens.setup
        import widgets.record_item
        import widgets.simple_fields

        return Builder.load_file(os.path.join(os.path.dirname(__file__), "app.kv"))


if __name__ == "__main__":
    WageBookApp().run()
