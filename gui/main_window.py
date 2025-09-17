import tkinter as tk
from tkinter import ttk, messagebox
import threading
from core import disk_query, diskpart_ops, eject


class MainWindow:
    def __init__(self, root: tk.Tk):
        self.root = root
        self._build_ui()
        self.refresh_disks()

    def _build_ui(self):
        frm_top = ttk.Frame(self.root)
        frm_top.pack(fill='x', padx=8, pady=4)
        ttk.Button(frm_top, text='刷新磁盘', command=self.refresh_disks).pack(side='left')
        ttk.Button(frm_top, text='脱机->联机', command=self.offline_online).pack(side='left', padx=6)
        ttk.Button(frm_top, text='多策略弹出', command=self.eject_selected).pack(side='left', padx=6)

        self.tree = ttk.Treeview(self.root, columns=('index', 'model', 'letters', 'size'), show='headings', height=8)
        self.tree.heading('index', text='索引')
        self.tree.heading('model', text='型号')
        self.tree.heading('letters', text='盘符')
        self.tree.heading('size', text='大小(GB)')
        self.tree.pack(fill='both', expand=True, padx=8, pady=4)

        frm_log = ttk.LabelFrame(self.root, text='日志')
        frm_log.pack(fill='both', expand=True, padx=8, pady=4)
        self.txt_log = tk.Text(frm_log, height=10)
        self.txt_log.pack(fill='both', expand=True)

        self.status = tk.StringVar(value='就绪')
        ttk.Label(self.root, textvariable=self.status, anchor='w').pack(fill='x', padx=8, pady=(0,4))

    def log(self, msg: str):
        self.txt_log.insert('end', msg + '\n')
        self.txt_log.see('end')

    def refresh_disks(self):
        try:
            disks = disk_query.query_disks(refresh=True)
        except Exception as e:
            messagebox.showerror('错误', str(e))
            return
        for i in self.tree.get_children():
            self.tree.delete(i)
        for d in disks:
            size_gb = d.size / (1024**3) if d.size else 0
            self.tree.insert('', 'end', iid=str(d.index), values=(d.index, d.model, ','.join(d.letters), f"{size_gb:.1f}"))
        self.log('刷新磁盘完成')

    def _selected_index(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo('提示', '请选择一个磁盘')
            return None
        return int(sel[0])

    def offline_online(self):
        idx = self._selected_index()
        if idx is None:
            return
        if not messagebox.askyesno('确认', '执行脱机->联机可能导致未保存数据丢失，继续?'):
            return
        def task():
            self.status.set('执行脱机->联机...')
            try:
                out = diskpart_ops.offline_online(idx)
                self.log(out)
            except Exception as e:
                self.log(f'错误: {e}')
            finally:
                try:
                    self.refresh_disks()
                except Exception:
                    pass
                self.status.set('就绪')
        threading.Thread(target=task, daemon=True).start()

    def eject_selected(self):
        idx = self._selected_index()
        if idx is None:
            return
        disk = disk_query.find_disk_by_index(idx)
        if not disk:
            return
        if not messagebox.askyesno('确认', '多策略弹出可能会将磁盘离线或移除，请确认已保存数据。继续?'):
            return
        def task():
            self.status.set('多策略弹出中...')
            try:
                result = eject.eject_disk(disk.index, disk.letters)
                self.log(f"[弹出结果] success={result['success']} stage={result['stage']}")
                for line in result.get('details', []):
                    self.log(line)
                if result['stage'] == 'disk_offline':
                    self.log('磁盘已离线，可尝试物理拔出。若需恢复，可使用“脱机->联机”重新上线。')
                elif result['stage'] == 'pnp_remove':
                    self.log('PnP 设备已请求移除，若盘符已消失可安全拔出。')
                elif not result['success']:
                    self.log('所有策略未成功，可尝试手动在资源管理器中“安全移除硬件”。')
            except Exception as e:
                self.log(f'弹出执行错误: {e}')
            finally:
                try:
                    self.refresh_disks()
                except Exception:
                    pass
                self.status.set('就绪')
        threading.Thread(target=task, daemon=True).start()
