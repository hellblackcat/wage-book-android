# -*- coding: utf-8 -*-
"""明细卡片（新增记录页）"""
from kivy.properties import DictProperty, NumericProperty
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDIconButton
from kivymd.uix.chip import MDChip
from kivymd.uix.textfield import MDTextField


class _RecordItemCard(MDBoxLayout):
    """KV for 循环中的明细行"""
    idx = NumericProperty(0)
    item_data = DictProperty()

    def on_remove(self, index):
        pass  # 实际由 parent screen 处理

    def on_refresh(self, index):
        pass  # 实际由 parent screen 处理
