import os
import sys
import json
import time
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from config import Config
from extractor import LinkExtractor
from scraper import AudioScraper
from downloader import AudioDownloader, AudioInfo


class TaskManager:
    def __init__(self):
        self.tasks = []
        self.task_id_counter = 0
    
    def add_task(self, play_ids, task_type="full"):
        self.task_id_counter += 1
        task = {
            "id": self.task_id_counter,
            "play_ids": play_ids,
            "type": task_type,
            "status": "pending",
            "progress": 0,
            "message": "等待中",
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "audio_infos": []
        }
        self.tasks.append(task)
        return task["id"]
    
    def update_task(self, task_id, **kwargs):
        for task in self.tasks:
            if task["id"] == task_id:
                task.update(kwargs)
                break
    
    def get_task(self, task_id):
        for task in self.tasks:
            if task["id"] == task_id:
                return task
        return None
    
    def get_all_tasks(self):
        return self.tasks


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("音频批量下载工具")
        self.root.geometry("900x700")
        
        self.task_manager = TaskManager()
        self.current_task_id = None
        self.is_running = False
        
        self.setup_ui()
    
    def setup_ui(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.tab_tasks = ttk.Frame(self.notebook)
        self.tab_config = ttk.Frame(self.notebook)
        self.tab_logs = ttk.Frame(self.notebook)
        
        self.notebook.add(self.tab_tasks, text="任务管理")
        self.notebook.add(self.tab_config, text="配置设置")
        self.notebook.add(self.tab_logs, text="运行日志")
        
        self.setup_tasks_tab()
        self.setup_config_tab()
        self.setup_logs_tab()
    
    def setup_tasks_tab(self):
        main_frame = ttk.Frame(self.tab_tasks)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        input_frame = ttk.LabelFrame(main_frame, text="添加任务")
        input_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(input_frame, text="播放ID (每行一个):").pack(anchor=tk.W, padx=5, pady=5)
        
        self.task_input = scrolledtext.ScrolledText(input_frame, height=6)
        self.task_input.pack(fill=tk.X, padx=5, pady=5)
        
        btn_frame = ttk.Frame(input_frame)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(btn_frame, text="添加任务", command=self.add_task).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="从文件导入", command=self.import_from_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="清空输入", command=lambda: self.task_input.delete("1.0", tk.END)).pack(side=tk.LEFT, padx=5)
        
        task_list_frame = ttk.LabelFrame(main_frame, text="任务列表")
        task_list_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        columns = ("ID", "类型", "状态", "进度", "消息", "创建时间")
        self.task_tree = ttk.Treeview(task_list_frame, columns=columns, show="headings", height=10)
        
        for col in columns:
            self.task_tree.heading(col, text=col)
            self.task_tree.column(col, width=100)
        
        self.task_tree.column("消息", width=200)
        self.task_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.task_tree.bind("<Double-1>", self.on_task_double_click)
        
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=5)
        
        self.btn_start = ttk.Button(control_frame, text="开始执行", command=self.start_tasks)
        self.btn_start.pack(side=tk.LEFT, padx=5)
        
        self.btn_stop = ttk.Button(control_frame, text="停止", command=self.stop_tasks, state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(control_frame, text="删除任务", command=self.delete_task).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="清空已完成", command=self.clear_completed).pack(side=tk.LEFT, padx=5)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, pady=5)
    
    def setup_config_tab(self):
        main_frame = ttk.Frame(self.tab_config)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        config_frame = ttk.LabelFrame(main_frame, text="配置参数")
        config_frame.pack(fill=tk.BOTH, expand=True)
        
        self.config_entries = {}
        
        config_items = [
            ("base_url", "网站URL:", "https://i275.com"),
            ("play_url_template", "播放链接模板:", "https://i275.com/play/{}.html"),
            ("cookie", "Cookie:", ""),
            ("request_interval", "请求间隔(秒):", "0.1"),
            ("request_timeout", "请求超时(秒):", "10"),
            ("max_retries", "最大重试次数:", "3"),
            ("max_workers", "最大并发数:", "32"),
            ("download_timeout", "下载超时(秒):", "60"),
            ("default_download_dir", "下载目录:", "downloads"),
            ("json_output_file", "JSON输出文件:", "audio_infos.json"),
            ("input_file", "输入文件:", "input.txt"),
            ("output_file", "输出文件:", "output.txt"),
        ]
        
        for i, (key, label, default) in enumerate(config_items):
            row = i // 2
            col = (i % 2) * 2
            
            ttk.Label(config_frame, text=label).grid(row=row, column=col, sticky=tk.W, padx=10, pady=5)
            
            if key in ["default_download_dir"]:
                entry_frame = ttk.Frame(config_frame)
                entry_frame.grid(row=row, column=col+1, sticky=tk.W, padx=10, pady=5)
                
                entry = ttk.Entry(entry_frame, width=30)
                entry.pack(side=tk.LEFT)
                entry.insert(0, Config._get_config().get(key, default))
                
                ttk.Button(entry_frame, text="浏览", command=lambda e=entry: self.browse_folder(e)).pack(side=tk.LEFT, padx=5)
            else:
                entry = ttk.Entry(config_frame, width=35)
                entry.grid(row=row, column=col+1, sticky=tk.W, padx=10, pady=5)
                entry.insert(0, Config._get_config().get(key, default))
            
            self.config_entries[key] = entry
        
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=10)
        
        ttk.Button(btn_frame, text="保存配置", command=self.save_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="重置默认", command=self.reset_config).pack(side=tk.LEFT, padx=5)
    
    def setup_logs_tab(self):
        self.log_text = scrolledtext.ScrolledText(self.tab_logs, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        btn_frame = ttk.Frame(self.tab_logs)
        btn_frame.pack(pady=5)
        
        ttk.Button(btn_frame, text="清空日志", command=self.clear_logs).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="导出日志", command=self.export_logs).pack(side=tk.LEFT, padx=5)
    
    def log(self, message):
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
    
    def add_task(self):
        content = self.task_input.get("1.0", tk.END).strip()
        if not content:
            messagebox.showwarning("警告", "请输入播放ID")
            return
        
        play_ids = [line.strip() for line in content.split("\n") if line.strip()]
        
        task_id = self.task_manager.add_task(play_ids, "full")
        self.log(f"添加任务 #{task_id}, 包含 {len(play_ids)} 个播放ID")
        
        self.task_input.delete("1.0", tk.END)
        self.refresh_task_list()
    
    def import_from_file(self):
        filename = filedialog.askopenfilename(
            title="选择输入文件",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                play_ids = LinkExtractor.extract_play_content(content)
                
                if not play_ids:
                    play_ids = [line.strip() for line in content.split("\n") if line.strip()]
                
                if play_ids:
                    task_id = self.task_manager.add_task(play_ids, "full")
                    self.log(f"从文件导入任务 #{task_id}, 包含 {len(play_ids)} 个播放ID")
                    self.refresh_task_list()
                else:
                    messagebox.showwarning("警告", "文件中未找到有效的播放ID")
                    
            except Exception as e:
                messagebox.showerror("错误", f"读取文件失败: {e}")
    
    def refresh_task_list(self):
        for item in self.task_tree.get_children():
            self.task_tree.delete(item)
        
        for task in self.task_manager.get_all_tasks():
            self.task_tree.insert("", tk.END, values=(
                task["id"],
                task["type"],
                task["status"],
                f"{task['progress']}%",
                task["message"],
                task["created_at"]
            ))
    
    def on_task_double_click(self, event):
        selection = self.task_tree.selection()
        if selection:
            item = self.task_tree.item(selection[0])
            task_id = item["values"][0]
            task = self.task_manager.get_task(task_id)
            
            if task and task.get("audio_infos"):
                info = f"任务 #{task_id}\n"
                info += f"播放ID数量: {len(task['play_ids'])}\n"
                info += f"音频信息数量: {len(task['audio_infos'])}\n"
                
                for audio in task["audio_infos"][:5]:
                    info += f"\n- {audio.get('name', '未知')} - {audio.get('artist', '未知')}"
                
                if len(task["audio_infos"]) > 5:
                    info += f"\n... 还有 {len(task['audio_infos']) - 5} 个"
                
                messagebox.showinfo("任务详情", info)
    
    def delete_task(self):
        selection = self.task_tree.selection()
        if selection:
            item = self.task_tree.item(selection[0])
            task_id = item["values"][0]
            
            for i, task in enumerate(self.task_manager.tasks):
                if task["id"] == task_id:
                    self.task_manager.tasks.pop(i)
                    break
            
            self.log(f"删除任务 #{task_id}")
            self.refresh_task_list()
    
    def clear_completed(self):
        self.task_manager.tasks = [t for t in self.task_manager.tasks if t["status"] not in ["completed", "failed"]]
        self.log("已清空已完成的任务")
        self.refresh_task_list()
    
    def start_tasks(self):
        pending_tasks = [t for t in self.task_manager.get_all_tasks() if t["status"] == "pending"]
        
        if not pending_tasks:
            messagebox.showwarning("警告", "没有待执行的任务")
            return
        
        self.is_running = True
        self.btn_start.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        
        thread = threading.Thread(target=self.run_tasks_thread, args=(pending_tasks,))
        thread.daemon = True
        thread.start()
    
    def run_tasks_thread(self, tasks):
        for task in tasks:
            if not self.is_running:
                break
            
            self.current_task_id = task["id"]
            self.root.after(0, lambda: self.log(f"开始执行任务 #{task['id']}"))
            
            self.task_manager.update_task(task["id"], status="running", message="正在提取链接")
            self.root.after(0, self.refresh_task_list)
            
            try:
                urls = LinkExtractor.build_play_urls(task["play_ids"])
                
                self.task_manager.update_task(task["id"], progress=10, message="正在获取音频信息")
                self.root.after(0, self.refresh_task_list)
                
                scraper = AudioScraper()
                scraper.init_session()
                
                audio_infos = scraper.process_urls(urls)
                
                task["audio_infos"] = audio_infos
                
                self.task_manager.update_task(
                    task["id"], 
                    progress=50, 
                    message=f"获取到 {len(audio_infos)} 个音频"
                )
                self.root.after(0, self.refresh_task_list)
                
                if audio_infos:
                    scraper.save_to_json(audio_infos)
                    
                    self.task_manager.update_task(task["id"], progress=60, message="正在下载音频")
                    self.root.after(0, self.refresh_task_list)
                    
                    downloader = AudioDownloader(
                        max_workers=Config.MAX_WORKERS,
                        max_retries=Config.MAX_RETRIES,
                        download_dir=Config.DEFAULT_DOWNLOAD_DIR
                    )
                    
                    success = downloader.download()
                    
                    self.task_manager.update_task(
                        task["id"],
                        progress=100,
                        status="completed" if success else "failed",
                        message="下载完成" if success else "下载失败"
                    )
                else:
                    self.task_manager.update_task(
                        task["id"],
                        status="failed",
                        message="未获取到音频信息"
                    )
                
            except Exception as e:
                self.log(f"任务 #{task['id']} 执行失败: {e}")
                self.task_manager.update_task(
                    task["id"],
                    status="failed",
                    message=str(e)
                )
            
            self.root.after(0, self.refresh_task_list)
        
        self.root.after(0, self.on_tasks_complete)
    
    def on_tasks_complete(self):
        self.is_running = False
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self.log("所有任务执行完成")
    
    def stop_tasks(self):
        self.is_running = False
        self.log("正在停止任务...")
    
    def browse_folder(self, entry):
        folder = filedialog.askdirectory()
        if folder:
            entry.delete(0, tk.END)
            entry.insert(0, folder)
    
    def save_config(self):
        try:
            updates = {}
            for key, entry in self.config_entries.items():
                value = entry.get()
                
                if key in ["request_interval", "request_timeout", "max_retries", "max_workers", "download_timeout"]:
                    try:
                        value = float(value) if "." in value else int(value)
                    except ValueError:
                        messagebox.showerror("错误", f"配置项 {key} 必须是数字")
                        return
                
                updates[key] = value
            
            Config.update_multiple(updates)
            self.log("配置已保存")
            messagebox.showinfo("成功", "配置已保存")
            
        except Exception as e:
            messagebox.showerror("错误", f"保存配置失败: {e}")
    
    def reset_config(self):
        if messagebox.askyesno("确认", "确定要重置为默认配置吗?"):
            from config import get_default_config, save_config
            config = get_default_config()
            save_config(config)
            Config.reload()
            self.log("配置已重置为默认值")
            messagebox.showinfo("成功", "配置已重置")
    
    def clear_logs(self):
        self.log_text.delete("1.0", tk.END)
    
    def export_logs(self):
        filename = filedialog.asksaveasfilename(
            title="导出日志",
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.log_text.get("1.0", tk.END))
                self.log(f"日志已导出到: {filename}")
            except Exception as e:
                messagebox.showerror("错误", f"导出日志失败: {e}")


def main():
    root = tk.Tk()
    app = App(root)
    root.mainloop()


if __name__ == "__main__":
    main()