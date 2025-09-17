import tkinter as tk
from tkinter import ttk, messagebox
import threading
import webbrowser
from core import disk_query, diskpart_ops, eject


class MainWindow:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.show_all_var = tk.BooleanVar(value=False)  # 新增：显示所有磁盘
        self._build_ui()
        self.refresh_disks()

    def _build_ui(self):
        frm_top = ttk.Frame(self.root)
        frm_top.pack(fill='x', padx=8, pady=4)
        ttk.Button(frm_top, text='刷新磁盘', command=self.refresh_disks).pack(side='left')
        # 新增：显示所有磁盘复选框
        ttk.Checkbutton(frm_top, text='显示所有磁盘', variable=self.show_all_var, command=self.refresh_disks).pack(side='left', padx=8)
        # 新增：单独脱机、联机按钮（保存引用以便禁用/启用）
        self.btn_offline = ttk.Button(frm_top, text='脱机', command=self.offline_only)
        self.btn_offline.pack(side='left', padx=6)
        self.btn_online = ttk.Button(frm_top, text='联机', command=self.online_only)
        self.btn_online.pack(side='left', padx=6)
        # 保留原组合操作
        self.btn_off_on = ttk.Button(frm_top, text='脱机->联机', command=self.offline_online)
        self.btn_off_on.pack(side='left', padx=6)
        self.btn_eject = ttk.Button(frm_top, text='多策略弹出', command=self.eject_selected)
        self.btn_eject.pack(side='left', padx=6)
        # 新增：帮助按钮
        ttk.Button(frm_top, text='帮助', command=self.show_help).pack(side='right')

        # 表格新增“类型”列
        self.tree = ttk.Treeview(self.root, columns=('index', 'model', 'letters', 'size', 'type'), show='headings', height=8)
        self.tree.heading('index', text='索引')
        self.tree.heading('model', text='型号')
        self.tree.heading('letters', text='盘符')
        self.tree.heading('size', text='大小(GB)')
        self.tree.heading('type', text='类型')
        self.tree.pack(fill='both', expand=True, padx=8, pady=4)
        # 选择变化时更新按钮可用性
        self.tree.bind('<<TreeviewSelect>>', self._update_actions_state)

        frm_log = ttk.LabelFrame(self.root, text='日志')
        frm_log.pack(fill='both', expand=True, padx=8, pady=4)
        self.txt_log = tk.Text(frm_log, height=10)
        self.txt_log.pack(fill='both', expand=True)

        self.status = tk.StringVar(value='就绪')
        ttk.Label(self.root, textvariable=self.status, anchor='w').pack(fill='x', padx=8, pady=(0,4))

    def _update_actions_state(self, _evt=None):
        disk = self._get_selected_disk(show_message=False)
        enable = bool(disk and disk.is_external)
        state = 'normal' if enable else 'disabled'
        for btn in (self.btn_offline, self.btn_online, self.btn_off_on, self.btn_eject):
            btn.state(['!disabled'] if state == 'normal' else ['disabled'])

    def log(self, msg: str):
        self.txt_log.insert('end', msg + '\n')
        self.txt_log.see('end')

    def refresh_disks(self):
        try:
            disks = disk_query.query_disks(refresh=True, show_all=self.show_all_var.get())
        except Exception as e:
            messagebox.showerror('错误', str(e))
            return
        for i in self.tree.get_children():
            self.tree.delete(i)
        for d in disks:
            size_gb = d.size / (1024**3) if d.size else 0
            dtype = '外接' if getattr(d, 'is_external', False) else '内置'
            self.tree.insert('', 'end', iid=str(d.index), values=(d.index, d.model, ','.join(d.letters), f"{size_gb:.1f}", dtype))
        self.log('刷新磁盘完成')
        self._update_actions_state()

    def _selected_index(self):
        sel = self.tree.selection()
        if not sel:
            return None
        return int(sel[0])

    def _get_selected_disk(self, show_message: bool = True):
        idx = self._selected_index()
        if idx is None:
            if show_message:
                messagebox.showinfo('提示', '请选择一个磁盘')
            return None
        disk = disk_query.find_disk_by_index(idx)
        if not disk:
            if show_message:
                messagebox.showwarning('提示', '未找到所选磁盘，请刷新后重试')
            return None
        return disk

    def offline_only(self):
        disk = self._get_selected_disk()
        if not disk:
            return
        if not getattr(disk, 'is_external', False):
            messagebox.showinfo('提示', '为防误操作，已禁止对内置固定盘执行脱机。')
            return
        if not messagebox.askyesno('确认', '将把所选磁盘置为“脱机”，可能导致未保存数据丢失，继续?'):
            return
        def task():
            self.status.set('执行脱机...')
            try:
                out = diskpart_ops.offline_disk(disk.index)
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

    def online_only(self):
        disk = self._get_selected_disk()
        if not disk:
            return
        if not getattr(disk, 'is_external', False):
            messagebox.showinfo('提示', '为防误操作，已禁止对内置固定盘执行联机。')
            return
        def task():
            self.status.set('执行联机...')
            try:
                out = diskpart_ops.online_disk(disk.index)
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

    def offline_online(self):
        disk = self._get_selected_disk()
        if not disk:
            return
        if not getattr(disk, 'is_external', False):
            messagebox.showinfo('提示', '为防误操作，已禁止对内置固定盘执行脱机->联机。')
            return
        if not messagebox.askyesno('确认', '执行脱机->联机可能导致未保存数据丢失，继续?'):
            return
        def task():
            self.status.set('执行脱机->联机...')
            try:
                out = diskpart_ops.offline_online(disk.index)
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
        disk = self._get_selected_disk()
        if not disk:
            return
        if not getattr(disk, 'is_external', False):
            messagebox.showinfo('提示', '为防误操作，已禁止对内置固定盘执行弹出。')
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
                    self.log('磁盘已离线，可尝试物理拔出。若需恢复，可使用“联机”或“脱机->联机”重新上线。')
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

    def show_help(self):
        repo_url = 'https://github.com/SiriusPaul/QuickForcedEjectPortableDisk'
        msg = (
            '使用说明:\n'
            '1) 选择上方表格中的目标磁盘。\n'
            '2) 可点击“脱机->联机”快速释放异常占用；\n'
            '   若仍然无法弹出，可多试几次，或使用“脱机”将磁盘暂时离线；点击“联机”恢复；\n'
            '3) “多策略弹出”会尝试 Shell 弹出/卷卸载/PNP 移除/离线等步骤；\n'
            '4) 勾选“显示所有磁盘”可查看内置盘，但已禁止对内置盘执行危险操作。\n\n'
            'Tips (EN): Select a disk, use Offline/Online, or Offline→Online to release locks.\n'
            'Multi-strategy Eject tries Shell/Volume/PnP/Offline in order.\n\n'
            '若该工具对您有用，可以为该项目点个 star，谢谢！\n'
            'If this tool is helpful to you, please star it on GitHub. Thanks!\n'
            'version 1.0'
        )
        win = tk.Toplevel(self.root)
        win.title('帮助 / Help')
        win.transient(self.root)
        win.resizable(False, False)
        lbl = tk.Label(win, text=msg, justify='left', anchor='w', padx=10, pady=10)
        lbl.pack(fill='both', expand=True)
        link = tk.Label(win, text=repo_url, fg='blue', cursor='hand2', padx=10)
        link.configure(font=(link.cget('font'), 0, 'underline'))
        link.pack(anchor='w')
        link.bind('<Button-1>', lambda e: webbrowser.open(repo_url))
        btn = ttk.Button(win, text='关闭 / Close', command=win.destroy)
        btn.pack(pady=(6, 10))
        win.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - win.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - win.winfo_height()) // 2
        win.geometry(f'+{x}+{y}')
