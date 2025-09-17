# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for QuickForcedEjectPortableDisk
# 生成方式: pyinstaller app.spec
# 若需要目录模式(启动更快)删除 one-file 风格: 可改用命令行 pyinstaller app.spec --onedir 或调整为含 COLLECT 段。
# 如需管理员权限启动, 可自行创建 manifest.xml, 然后在 EXE(...) 里加 manifest='manifest.xml'

block_cipher = None


a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[('logo.ico', '.')],  # 运行期若需访问原始图标放入同目录
    hiddenimports=[],            # 如打包后缺模块, 将模块名追加到此列表
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],            # 可放置自定义运行期 hook, 例如强制设置编码等
    excludes=[],                 # 可排除不需要的库减小体积, 例如 ['tests', 'tkinter.test']
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,             # 设 True 可将 .pyc 解压到文件夹方便调试
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# 单文件(onefile)模式: 无 COLLECT 段。若想要 onedir 模式, 参考官方文档在此之后添加 COLLECT。
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='QuickPortableDiskTool',
    icon='logo.ico',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,              # 若已安装 UPX 可减小体积; 无 UPX 仍可设 True(自动忽略)
    upx_exclude=[],
    runtime_tmpdir=None,   # 可指定临时解压目录; 默认系统临时目录
    console=False,         # GUI 程序隐藏控制台
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # manifest='manifest.xml',  # 需要管理员权限时取消注释并提供 manifest 文件
)

