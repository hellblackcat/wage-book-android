[app]

title = 工资记账表
package.name = wagebook
package.domain = com.wagebook
source.dir = .
source.include_exts = py,png,jpg,kv,atlas

version = 1.0.0

requirements = python3,kivy==2.3.1,kivymd==2.0.0,pillow,sqlite3

orientation = portrait
fullscreen = 0

android.permissions = WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE
android.archs = arm64-v8a, armeabi-v7a
android.minapi = 21
android.api = 34

android.meta_data = android.app.launch_mode=singleTop

[buildozer]
log_level = 2
warn_on_root = 1
android.sdk_path = /home/runner/.buildozer/android/platform/android-sdk
