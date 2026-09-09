# 工资记账表 — 安卓版 SPEC

> 目标: 把桌面版 PySide6 工资记账表迁移为 KivyMD 安卓 App
> 状态: V1.0 | 日期: 2026-09-09

---

## 1. 概述

- **包名**: `com.wagebook.app`
- **应用名**: 工资记账表
- **核心功能**: 按天记录加工零件活，按月自动汇总工资/工时/出勤，支持智能拆条输入、型号管理
- **目标用户**: 工厂工人 / 计件工种
- **数据存储**: 本地 SQLite（`wage_book.db`），与桌面版共用同一文件格式（可直接复制迁移）

---

## 2. 核心业务（沿用桌面版）

### 2.1 数据模型（DB Schema）

沿用桌面版结构，部分字段新增：

```sql
-- 个人信息表（新增）
CREATE TABLE user (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL
);

-- 记录明细表（沿用）
CREATE TABLE records (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    date           TEXT    NOT NULL,   -- '2026-09-01'
    shift_type     TEXT    NOT NULL DEFAULT 'day',  -- 'day' | 'night'
    start_time     TEXT,                           -- '20:00'
    end_time       TEXT,                           -- '04:00'
    work_hours     REAL    DEFAULT 0,
    master_hours   REAL    DEFAULT 0,
    overtime_hours REAL    DEFAULT 0,
    work_type      TEXT    DEFAULT '',
    part_model     TEXT    DEFAULT '',
    quantity       INTEGER DEFAULT 0,
    price_milli    INTEGER DEFAULT 0,  -- 元×1000 (厘)
    wage_fen       INTEGER DEFAULT 0,  -- 元×100 (分)
    wage_manual    INTEGER DEFAULT 0,
    charge_mode    INTEGER NOT NULL DEFAULT 0,  -- 0=计件 1=计时
    charge_hours   REAL    NOT NULL DEFAULT 0,
    created_at     TEXT    DEFAULT (datetime('now','localtime'))
);

-- 型号表（沿用，新增 default_type）
CREATE TABLE models (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT    NOT NULL UNIQUE,
    default_type TEXT    DEFAULT '',
    piece_milli  INTEGER NOT NULL DEFAULT 0,
    hourly_milli INTEGER NOT NULL DEFAULT 0,
    created_at   TEXT    DEFAULT (datetime('now','localtime')),
    updated_at   TEXT
);
```

### 2.2 关键业务规则（沿用桌面版）

| 规则 | 说明 |
|------|------|
| 白班 | 默认 08:00~17:00，扣 1h 午休 = 8h |
| 夜班 | 默认 20:00~次日 04:00，8h，不扣休息 |
| 白班加班 | max(0, 工作时长 − 8) |
| 夜班加班 | max(0, 下班时刻 − 4:00)，最大 8h，到 12:00 止 |
| 夜班归属日 | 实际起班日 − 1 天 |
| 单价精度 | 3 位小数（厘），整数 = 元 × 1000 |
| 工资精度 | 2 位小数（分），整数 = 元 × 100 |
| 智能解析 | 日期/工时共享一段；无型号行继承上一型号；`调试/压伤/报废` 等忽略 |
| 型号单价修改 | 自动回写所有历史明细 unit_price + wage，重新汇总 day_record.total_wage，写入变更日志 |

---

## 3. UI/UX 设计

### 3.1 设计原则
- **清爽简洁**：白底 + 淡色卡片，大面积留白
- **主色调**：蓝（`#1677FF`），类似桌面版 Ant Design 风格
- **文字**：深灰 `#1F2329`，字号适中（14sp 正文，16sp 标题）
- **触控友好**：所有按钮/输入框最小高度 48dp，间距充足
- **字体**：系统默认（安卓 Roboto）

### 3.2 屏幕结构

```
┌─────────────────────────────┐
│  顶部 AppBar：标题 + 用户名  │  ← 始终可见
├─────────────────────────────┤
│                             │
│       主内容区               │  ← 可滚动
│                             │
├─────────────────────────────┤
│  底部导航栏（4个Tab）        │
│  记录  统计  型号  我的      │
└─────────────────────────────┘
```

### 3.3 Tab 1 — 记录（默认首页）

**顶部筛选栏**
- 月份选择器（当前月，左/右切换月份）
- 「+ 新增」浮动按钮（右下角 FAB）

**当日记录列表**
- 按日期倒序分组，每组顶部显示日期
- 每条记录卡片：
  - 班别标签（白班/夜班）+ 时间范围
  - 型号 + 类型 + 数量/时长
  - 金额（右下方，加粗）
- 卡片可左滑删除 / 点击编辑

**新增记录弹窗（全屏）**
- 顶部：班别切换（白班 / 夜班）
- 日期选择（默认今天）
- 出勤时间（起/止）
- 工作时长 / 大工时长（自动算加班）
- ⭐ 智能输入区（可折叠）：
  - 多行文本框，贴入考勤文字
  - 「智能解析」按钮 → 预览拆条结果（手机卡片式）
  - 用户确认后自动填入下方明细区
- 批量明细区（可添加多条）：
  - 计费方式切换（计件/计时）
  - 型号（自动补全）+ 类型 + 数量/时长 + 单价
  - 自动算金额
- 底部「保存」按钮

### 3.4 Tab 2 — 统计

**顶部月份选择**

**5 个指标卡片（2行3列）**
- 本月工薪（突出显示）
- 出勤天数
- 总工时
- 大工工时
- 夜班天数

**型号汇总列表**
- 型号 / 当月数量 / 当月金额
- 支持按金额排序

### 3.5 Tab 3 — 型号管理

**列表视图**
- 型号 / 默认类型 / 计件单价 / 计时单价
- 点击 → 编辑弹窗（只改价格和类型，不改型号名）
- 底部「+ 新增型号」按钮

**新增/编辑型号弹窗**
- 型号名称（新增时必填）
- 默认类型（自由输入）
- 计件单价 / 计时单价（可空）

### 3.6 Tab 4 — 我的

- 用户名（点击可修改）
- App 版本号
- 数据备份说明（复制 db 文件路径 / 分享）
- 关于

---

## 4. 首次进入流程

```
启动 → 检查 user 表是否有记录
  ├─ 无 → 弹出"请输入您的姓名"单次设置（只出现一次）
  └─ 有 → 直接进入首页
```

---

## 5. 技术方案

| 项 | 选择 |
|---|------|
| 框架 | Kivy + KivyMD |
| 语言 | Python 3 |
| 数据库 | SQLite（`wage_book.db`，与桌面版同格式） |
| 打包工具 | buildozer |
| 业务逻辑 | 直接复用桌面版 `wage_book.pyw` 的 DB 类 + 计算函数 |
| UI 逻辑 | 全部重写（KivyMD 组件） |
| 数据文件位置 | `App.get_application_config()` 返回的路径下 |

### 关键文件结构

```
工资记账表安卓版/
├── SPEC.md
├── main.py              # 入口，Kivy App 类
├── db.py                # 复用的数据库类（来自桌面版，略作适配）
├── business.py          # 复用的计算/解析函数（来自桌面版）
├── screens/
│   ├── records.py       # 记录 Tab
│   ├── stats.py         # 统计 Tab
│   ├── models.py        # 型号管理 Tab
│   └── profile.py       # 我的 Tab
├── widgets/
│   ├── record_card.py   # 记录卡片
│   ├── stat_card.py     # 统计指标卡片
│   └── add_record.py    # 新增记录弹窗
├── requirements.txt
└── buildozer.spec
```

---

## 6. 验收标准

- [ ] 首次进入登记姓名，后续可修改
- [ ] 新增一条记录（手动填表），保存后出现在列表和统计中
- [ ] 智能输入解析 → 拆条预览 → 批量保存 N 条
- [ ] 夜班日期自动 −1 天，统计归属正确月份
- [ ] 编辑型号单价 → 历史明细同步更新
- [ ] 月度统计五指标与桌面版一致
- [ ] 关闭重启 App，数据持久
- [ ] 打包 APK 安装到真机，可正常打开使用

---

**END**
