# -*- coding: utf-8 -*-
"""ShellScreen — 包含内嵌 ScreenManager + 底部导航"""
from kivy.uix.screenmanager import ScreenManager, SlideTransition
from kivymd.uix.screen import MDScreen
from kivymd.uix.bottomnavigation import MDBottomNavigation
from kivymd.uix.bottomnavigationitem import MDBottomNavigationItem
from kivymd.uix.label import MDLabel
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.widget import Widget
from kivy.properties import StringProperty
from kivy.app import App


class ShellScreen(MDScreen):
    """主界面：顶部栏 + 内嵌 ScreenManager + 底部导航"""

    def switch_to(self, name):
        self.ids.inner_sm.current = name
        scr = self.ids.inner_sm.get_screen(name)
        if scr and hasattr(scr, 'on_enter'):
            scr.on_enter()
