import tkinter as tk
from tkinter import messagebox
from core import admin  # 若无 admin.py 可暂时移除此行并去掉权限逻辑
from gui.main_window import MainWindow


def main():
    # 如果还没放入 admin.py，可把下面两行改为 pass
    try:
        if hasattr(admin, 'ensure_admin') and not admin.ensure_admin():
            return
    except Exception:
        pass

    root = tk.Tk()
    root.title('可移动磁盘快速脱机/联机与弹出工具')
    MainWindow(root)
    root.mainloop()


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        messagebox.showerror('错误', str(e))
        raise

