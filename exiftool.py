import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
import subprocess
import os
import sys
import re
from tkcalendar import DateEntry  # 新增：引入第三方日期选择控件

# ==========================================
# 核心逻辑：执行 ExifTool
# ==========================================
def transfer_and_modify_exif_clean(exiftool_path, source_image, target_image, modifications, log_func):
    if not os.path.exists(exiftool_path):
        log_func("[✘] 错误: 找不到 ExifTool 请检查路径是否正确\n")
        return
    if not os.path.exists(target_image):
        log_func("[✘] 错误: 找不到目标照片文件\n")
        return

    # 构建基础命令
    cmd = [exiftool_path, "-m", "-overwrite_original"]

    if source_image and os.path.exists(source_image):
        cmd.extend(["-tagsFromFile", source_image, "-All:All", "--MakerNotes"])
        log_func(f"[►] 正在执行 [数据迁移 + 修改] 模式:\n源: {source_image}\n目标: {target_image}\n")
    else:
        log_func(f"[►] 正在执行 [直接修改] 模式 (无源文件):\n目标: {target_image}\n")

    if modifications:
        for tag, value in modifications.items():
            if value.strip():  
                cmd.append(f"-{tag}={value}")

    cmd.append(target_image)

    try:
        log_func("[►] 正在向照片注入 EXIF 数据...\n")
        creationflags = 0
        if os.name == 'nt':
            creationflags = subprocess.CREATE_NO_WINDOW
            
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, creationflags=creationflags)
        log_func("[✔] EXIF 数据已成功写入！\n")
        log_func("-" * 40 + "\n")
    except subprocess.CalledProcessError as e:
        log_func(f"[✘] ExifTool 执行失败\n详情: {e.stderr}\n")

# ==========================================
# UI 界面类
# ==========================================
class ExifToolGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("图片 EXIF 迁移与修改工具")
        self.root.geometry("620x840") # 稍微加宽一点以容纳时间控件
        
        self.exif_entries = {}

        if getattr(sys, 'frozen', False):
            exe_dir = os.path.dirname(sys.executable) 
        else:
            exe_dir = os.path.dirname(os.path.abspath(__file__)) 

        local_exiftool = os.path.join(exe_dir, "exiftool.exe")
        is_missing = False

        if os.path.exists(local_exiftool):
            default_exif_path = local_exiftool
        else:
            default_exif_path = "" 
            is_missing = True 

        # 1. 路径设置区
        frame_paths = tk.LabelFrame(root, text="第一步：文件与路径设置", padx=10, pady=10)
        frame_paths.pack(fill="x", padx=10, pady=5)

        self.exiftool_path = self.create_file_selector(frame_paths, "ExifTool 路径:", default_exif_path)
        self.source_path = self.create_file_selector(frame_paths, "源照片 (RAW/JPG ) 可不选:", "")
        self.target_path = self.create_file_selector(frame_paths, "目标照片 (JPG/TIFF) 必选:", "")

        # 2. EXIF 分类设置区
        tk.Label(root, text="第二步：自定义 EXIF (留空的项将保持原样不会被修改)", anchor="w").pack(fill="x", padx=10, pady=(10, 0))
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="x", padx=10, pady=5)

        # --- 标签页 1: 创作者与版权 ---
        tab1 = ttk.Frame(self.notebook)
        self.notebook.add(tab1, text="🖊 创作者与版权")
        self.add_entry(tab1, "Artist", "摄影师 :")
        self.add_entry(tab1, "Author", "作者 :")
        self.add_entry(tab1, "Copyright", "版权声明 (Copyright (c)) :")
        self.add_entry(tab1, "Software", "处理软件 (如 Adobe Photoshop) :")
        self.add_entry(tab1, "ImageDescription", "照片描述 :")
        self.add_entry(tab1, "UserComment", "用户备注 (如 拍摄于2023年) :")
        self.add_entry(tab1, "Rating", "星级评分 (如 填 1-5) :")

        # --- 标签页 2: 相机与镜头 ---
        tab2 = ttk.Frame(self.notebook)
        self.notebook.add(tab2, text="📷 相机与镜头")
        self.add_entry(tab2, "Make", "相机制造商 (如 SONY) :")
        self.add_entry(tab2, "Model", "相机型号 (如 D850) :")
        self.add_entry(tab2, "LensMake", "镜头品牌 (如 Nikkor) :")
        self.add_entry(tab2, "LensModel", "镜头型号 (如 24-70mm f2.8) :")

        # --- 标签页 3: 曝光参数 ---
        tab3 = ttk.Frame(self.notebook)
        self.notebook.add(tab3, text="☀ 曝光参数")
        self.add_entry(tab3, "FocalLength", "实际焦距mm (如 24) :")
        self.add_entry(tab3, "FocalLengthIn35mmFormat", "等效焦距mm (如 35) :")
        self.add_entry(tab3, "FNumber", "光圈 (如 1.8) :")
        self.add_entry(tab3, "ExposureTime", "快门速度 (如 1/250) :")
        self.add_entry(tab3, "ISO", "感光度 (如 100) :")
        self.add_entry(tab3, "ExposureCompensation", "曝光补偿 (如 +1/3) :")
        self.add_combobox(tab3, "Flash", "闪光灯 :", 
                          ["未设置", "未使用闪光灯", "使用闪光灯", "自动闪光灯", "红眼消除"])
        self.add_combobox(tab3, "WhiteBalance", "白平衡 :", 
                          ["未设置", "自动", "日光", "多云", "钨丝灯", "荧光灯", "手动"])

        # --- 标签页 4: 时间与 GPS ---
        tab4 = ttk.Frame(self.notebook)
        self.notebook.add(tab4, text="🌏 时间与 GPS")
        
        # 替换为全新的可视化日期时间控件
        self.add_datetime_picker(tab4, "DateTimeOriginal", "拍摄时间 :")
        self.add_datetime_picker(tab4, "CreateDate", "数字化时间 :")
        
        self.add_entry(tab4, "OffsetTimeOriginal", "时区偏移 (如 +08:00) :")
        self.add_entry(tab4, "GPSLatitude", "纬度 (如 39.9042) :")
        self.add_entry(tab4, "GPSLatitudeRef", "北/南纬 (填 N 或 S) :")
        self.add_entry(tab4, "GPSLongitude", "经度 (如 116.4074) :")
        self.add_entry(tab4, "GPSLongitudeRef", "东/西经 (填 E 或 W) :")
        self.add_entry(tab4, "GPSAltitude", "海拔高度 (m) :")

        # 3. 运行按钮
        btn_run = tk.Button(root, text="开始处理并写入 EXIF", bg="#4CAF50", fg="white", font=("微软雅黑", 12, "bold"), command=self.start_process)
        btn_run.pack(pady=10, ipadx=10, ipady=5)

        # 4. 日志输出区 
        frame_log = tk.LabelFrame(root, text="运行日志", padx=10, pady=5)
        frame_log.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(frame_log, wrap=tk.WORD, height=8)
        self.log_text.pack(fill="both", expand=True)

        if is_missing:
            self.log("[⚠] 未在当前目录下检测到 exiftool.exe 组件\n")
            self.log("[⚠] 请前往 ExifTool 官网下载解压后,在上方第一步手动【浏览】选择位置\n")
            self.log("-" * 40 + "\n")
        else:
            self.log("[✔] 已自动加载同级目录下的 ExifTool 引擎\n")
            self.log("-" * 40 + "\n")

    def create_file_selector(self, parent, label_text, default_val):
        row = tk.Frame(parent)
        row.pack(fill="x", pady=2)
        tk.Label(row, text=label_text, width=28, anchor="e").pack(side="left", padx=5)
        entry = tk.Entry(row)
        entry.pack(side="left", fill="x", expand=True)
        entry.insert(0, default_val)
        tk.Button(row, text="浏览...", command=lambda: self.browse_file(entry)).pack(side="right", padx=5)
        return entry

    def add_entry(self, parent, tag, label_text):
        row = tk.Frame(parent)
        row.pack(fill="x", pady=5, padx=5)
        tk.Label(row, text=label_text, width=28, anchor="e").pack(side="left", padx=5)
        entry = tk.Entry(row)
        entry.pack(side="left", fill="x", expand=True, padx=10)
        self.exif_entries[tag] = entry  

    def add_combobox(self, parent, tag, label_text, values):
        row = tk.Frame(parent)
        row.pack(fill="x", pady=5, padx=5)
        tk.Label(row, text=label_text, width=28, anchor="e").pack(side="left", padx=5)
        combo = ttk.Combobox(row, values=values, state="readonly")
        combo.pack(side="left", fill="x", expand=True, padx=10)
        combo.set(values[0]) 
        self.exif_entries[tag] = combo

    # ==========================================
    # 集成日历与时间的混合控件
    # ==========================================
    def add_datetime_picker(self, parent, tag, label_text):
        row = tk.Frame(parent)
        row.pack(fill="x", pady=5, padx=5)
        
        # 启用开关：默认不勾选，防止用户不小心覆盖了原有时间
        use_var = tk.BooleanVar(value=False)
        
        def toggle_state():
            # 【核心修改】：改回 normal 状态。
            # 既允许用户手动打字输入，又能解决 readonly 导致的日历箭头失效 Bug
            target_state = "normal" if use_var.get() else "disabled"
            cal.config(state=target_state)
            hr_cb.config(state=target_state)
            min_cb.config(state=target_state)
            sec_cb.config(state=target_state)

        # 左侧 Label 改为勾选框
        cb = tk.Checkbutton(row, text=label_text, variable=use_var, command=toggle_state, width=25, anchor="e")
        cb.pack(side="left", padx=5)

        # 右侧容器
        dt_frame = tk.Frame(row)
        dt_frame.pack(side="left", fill="x", expand=True, padx=10)

        # 1. 日期选择器 (初始设为 disabled)
        cal = DateEntry(dt_frame, width=12, background='#0078D7', foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd', state="disabled", locale='zh_CN')
        cal.pack(side="left", padx=(0, 5))

        # 2. 小时下拉框
        hr_var = tk.StringVar(value="12")
        hr_cb = ttk.Combobox(dt_frame, textvariable=hr_var, values=[f"{i:02d}" for i in range(24)], width=3, state="disabled")
        hr_cb.pack(side="left")
        tk.Label(dt_frame, text="时").pack(side="left")

        # 3. 分钟下拉框
        min_var = tk.StringVar(value="30")
        min_cb = ttk.Combobox(dt_frame, textvariable=min_var, values=[f"{i:02d}" for i in range(60)], width=3, state="disabled")
        min_cb.pack(side="left")
        tk.Label(dt_frame, text="分").pack(side="left")

        # 4. 秒数下拉框
        sec_var = tk.StringVar(value="00")
        sec_cb = ttk.Combobox(dt_frame, textvariable=sec_var, values=[f"{i:02d}" for i in range(60)], width=3, state="disabled")
        sec_cb.pack(side="left")
        tk.Label(dt_frame, text="秒").pack(side="left")

        # 创建一个代理类，响应 .get() 方法
        class DateTimeWidgetProxy:
            def get(self):
                if not use_var.get():
                    return "" 
                
                # 获取输入框里的字面文本（不管是用日历点的，还是用户键盘敲的）
                raw_date = cal.get().strip()
                if not raw_date:
                    return ""
                
                return f"{raw_date} {hr_var.get()}:{min_var.get()}:{sec_var.get()}"

        self.exif_entries[tag] = DateTimeWidgetProxy()

    def browse_file(self, entry_widget):
        filepath = filedialog.askopenfilename()
        if filepath:
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, os.path.normpath(filepath))

    def log(self, message):
        self.log_text.insert(tk.END, message)
        self.log_text.see(tk.END)
        self.root.update()

        # 用来包容用户各种乱七八糟的手动打字格式
    def smart_format_value(self, tag, value):
        value = value.strip()
        if not value: return value

        if tag == "FNumber":
            return re.sub(r'(?i)^f/?', '', value)
        elif tag in ["FocalLength", "FocalLengthIn35mmFormat", "GPSAltitude"]:
            return re.sub(r'(?i)\s*(mm|m)$', '', value)
        elif tag == "ISO":
            return re.sub(r'(?i)^iso\s*', '', value)
        elif tag == "ExposureTime":
            return re.sub(r'(?i)\s*(s|秒)$', '', value)
        elif tag == "GPSLatitudeRef":
            if re.search(r'(北|N)', value, re.IGNORECASE): return "N"
            if re.search(r'(南|S)', value, re.IGNORECASE): return "S"
        elif tag == "GPSLongitudeRef":
            if re.search(r'(东|E)', value, re.IGNORECASE): return "E"
            if re.search(r'(西|W)', value, re.IGNORECASE): return "W"
        elif tag == "Flash":
            flash_map = {"未使用闪光灯": "Off", "使用闪光灯": "On", "自动闪光灯": "Auto", "红眼消除": "On, Red-eye reduction"}
            if value in flash_map: return flash_map[value]
        elif tag == "WhiteBalance":
            wb_map = {"自动": "Auto", "日光": "Daylight", "多云": "Cloudy", "钨丝灯": "Tungsten", "荧光灯": "Fluorescent", "手动": "Manual"}
            if value in wb_map: return wb_map[value]
        elif tag in ["DateTimeOriginal", "CreateDate"]:
            v = re.sub(r'[年\-/\.]', ':', value)
            v = re.sub(r'[日]', ' ', v)
            v = re.sub(r'[月]', ':', v)
            v = re.sub(r'[时点分]', ':', v)
            v = re.sub(r'[秒]', '', v)
            v = re.sub(r':+', ':', v)
            v = re.sub(r'\s+', ' ', v).strip()
            parts = v.split(" ")
            if len(parts) == 1:
                return parts[0].strip(':') + " 12:00:00"
            else:
                date_part, time_part = parts[0].strip(':'), parts[1].strip(':')
                time_parts = [p for p in time_part.split(":") if p]
                while len(time_parts) < 3:
                    time_parts.append("00")
                return f"{date_part} {':'.join(time_parts[:3])}"

        return value

    def start_process(self):
        exiftool = self.exiftool_path.get().strip()
        source = self.source_path.get().strip()
        target = self.target_path.get().strip()

        if not target:
            messagebox.showwarning("警告", "必须选择要修改的【目标照片】！")
            return

        modifications = {}
        for tag, entry_widget in self.exif_entries.items():
            raw_value = entry_widget.get().strip()
            if raw_value and raw_value != "未设置": 
                formatted_value = self.smart_format_value(tag, raw_value)
                modifications[tag] = formatted_value

        if not source and not modifications:
            messagebox.showwarning("提示", "如果您不提供源照片进行迁移,请至少在下方填写一项需要修改的 EXIF 参数")
            return

        self.log("[➤] 开始任务...\n")
        if modifications:
            self.log("[►] 准备应用的自定义修改 (已智能格式化):\n")
            for k, v in modifications.items():
                self.log(f"   - {k}: {v}\n")
        else:
            self.log("[ℹ] 仅执行原生数据迁移\n")
            
        transfer_and_modify_exif_clean(exiftool, source, target, modifications, self.log)

# ==========================================
# 启动程序
# ==========================================
if __name__ == "__main__":
    root = tk.Tk()
    if os.name == 'nt':
        ttk.Style().theme_use("clam")
        
    app = ExifToolGUI(root)
    root.mainloop()