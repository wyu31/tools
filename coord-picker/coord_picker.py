#!/opt/homebrew/bin/python3.13
"""看图标坐标：鼠标移动实时显示像素坐标，回车给这个点起名字，点位列在右边并写进 txt。

用法：
    ./coord_picker.py [图.png]      不给参数则打开空画板，点 + 或把图拖进来
输出：
    与图同目录的 <图名>_coords.txt，每行 名字<TAB>x<TAB>y（右边列表就是它的内容）
操作：
    鼠标停在点上按回车(或空格/n/右键) 命名 / 左键 选中最近的点或复制坐标
    双击列表行或选中的点 改名 / Delete 或「删除」钮 删选中的点 / u 撤销最后一点 / ← → 或底部按钮 换同文件夹的上下一张 / o 选图 / Esc 取消选中

用 /opt/homebrew/bin/python3.13（brew install python-tk@3.13，Tk 9）。/usr/bin/python3 的 Tk 是 8.5.9，在新 macOS 上画布一片空白。
拖拽要 tkinterdnd2（python3.13 -m pip install --user --break-system-packages pillow tkinterdnd2），没装就只剩 + 按钮。
"""
import os, sys, tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    Root = TkinterDnD.Tk
except ImportError:  # ponytail: 没装 tkinterdnd2 就退化成只有 + 按钮
    DND_FILES, Root = None, tk.Tk

EXTS = (".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff")
BOARD = (1280, 720)
MARK, SEL = "#00a651", "#ff2d55"


def to_img(cx, cy, scale):
    """画布坐标转回原图像素坐标。"""
    return round(cx / scale), round(cy / scale)


def parse_drop(data):
    """tkdnd 的路径列表：带空格的路径用 {} 包住。"""
    paths, cur, depth = [], "", 0
    for ch in data:
        if ch == "{": depth += 1
        elif ch == "}": depth -= 1
        elif ch == " " and depth == 0:
            if cur: paths.append(cur); cur = ""
        else: cur += ch
    if cur: paths.append(cur)
    return [p for p in paths if p.lower().endswith(EXTS)]


def siblings(path):
    """同文件夹里的图，按名字排序，用来翻上下一张。"""
    d = os.path.dirname(path) or "."
    return sorted(os.path.join(d, f) for f in os.listdir(d) if f.lower().endswith(EXTS))


class Picker:
    def __init__(self, path):
        r = self.root = Root()
        r.title("Coord Picker"); r.configure(bg="white")
        self.im, self.pts, self.sel, self.last, self.scale = None, [], None, (0, 0), 1.0

        # width=1：标签只跟着窗口拉伸，文字变长不会反过来把画布挤小
        self.bar = tk.Label(r, text="", font=("Menlo", 15), anchor="w", padx=8, pady=4, bg="white", width=1)
        self.bar.grid(row=0, column=0, columnspan=2, sticky="ew")
        self.cv = tk.Canvas(r, width=BOARD[0], height=BOARD[1], highlightthickness=0, bg="white")
        self.cv.grid(row=1, column=0, sticky="nsew")

        side = tk.Frame(r, bg="white", padx=8, pady=4); side.grid(row=1, column=1, sticky="ns")
        head = tk.Frame(side, bg="white"); head.pack(fill="x")
        self.fname = tk.Entry(head, font=("Menlo", 13), relief="flat", bg="#f0f1f4", state="readonly", readonlybackground="#f0f1f4")
        self.fname.pack(side="left", fill="x", expand=True, ipady=3)
        tk.Button(head, text="Copy name", command=self.copy_name).pack(side="left", padx=(4, 0))
        tk.Label(side, text="Points (name  x  y)", bg="white", anchor="w").pack(fill="x", pady=(6, 0))
        self.lb = tk.Listbox(side, width=30, font=("Menlo", 13), activestyle="none",
                             selectbackground=SEL, selectforeground="white", exportselection=False)
        self.lb.pack(fill="both", expand=True)
        self.lb.bind("<<ListboxSelect>>", lambda _: self.select(self.lb.curselection()[0] if self.lb.curselection() else None))
        self.lb.bind("<Double-Button-1>", lambda _: self.rename())
        tk.Button(side, text="Delete selected (Delete)", command=self.delete).pack(fill="x", pady=(6, 0))
        tk.Button(side, text="Undo last (u)", command=self.undo).pack(fill="x", pady=(4, 0))
        tk.Button(side, text="Copy all (cmd+C)", command=lambda: self.copy(all_rows=True)).pack(fill="x", pady=(4, 0))

        foot = tk.Frame(r, bg="white", pady=6); foot.grid(row=2, column=0, columnspan=2, sticky="ew")
        tk.Button(foot, text="< Prev", command=lambda: self.step(-1)).pack(side="left", padx=8)
        tk.Button(foot, text="Next >", command=lambda: self.step(1)).pack(side="left")
        tk.Button(foot, text="Open (o)", command=self.pick).pack(side="left", padx=8)
        self.nav = tk.Label(foot, text="", bg="white", anchor="w", width=1); self.nav.pack(side="left", padx=8, fill="x", expand=True)
        r.grid_rowconfigure(1, weight=1); r.grid_columnconfigure(0, weight=1)

        if DND_FILES:
            self.cv.drop_target_register(DND_FILES)
            self.cv.dnd_bind("<<Drop>>", lambda e: [self.load(p) for p in parse_drop(e.data)[:1]])
        typing = lambda: isinstance(r.focus_get(), tk.Entry)
        # 不绑退出键：手一滑就关掉太伤，关窗口用红点或 cmd+W，数据本来就每次改动即时落盘
        for k, fn in {"u": self.undo, "o": self.pick, "<Escape>": lambda: self.select(None),
                      "<Delete>": self.delete, "<BackSpace>": self.delete,
                      "<Command-c>": self.copy, "<Control-c>": self.copy,
                      "<Left>": lambda: self.step(-1), "<Right>": lambda: self.step(1),
                      "<Return>": lambda: self.name_at(None), "<space>": lambda: self.name_at(None),
                      "n": lambda: self.name_at(None)}.items():
            r.bind(k, lambda _, fn=fn: typing() or fn())
        self.size = (0, 0)
        self.cv.bind("<Configure>", lambda e: self.im and (e.width, e.height) != self.size and self.fit())
        self.cv.bind("<Motion>", self.on_move)
        self.cv.bind("<Button-1>", self.on_left)
        self.cv.bind("<Double-Button-1>", lambda e: self.sel is not None and self.rename())
        for b in ("<Button-2>", "<Button-3>", "<Control-Button-1>"): self.cv.bind(b, self.name_at)
        self.load(path) if path else self.board()
        r.lift(); r.attributes("-topmost", True); r.after(200, lambda: r.attributes("-topmost", False))
        # Tk 会在内容尺寸变化时把窗口缩回「内容需要的大小」(最大化也会被弹回)，钉死几何就不再动
        r.update_idletasks(); r.geometry(r.geometry())
        r.mainloop()

    # 空画板：格子背景 + 加号按钮
    def board(self):
        cv = self.cv; self.im = None
        cv.delete("all"); cv.config(cursor="arrow")
        for x in range(0, BOARD[0], 40): cv.create_line(x, 0, x, BOARD[1], fill="#e7e9ef")
        for y in range(0, BOARD[1], 40): cv.create_line(0, y, BOARD[0], y, fill="#e7e9ef")
        cx, cy = BOARD[0] // 2, BOARD[1] // 2
        cv.create_oval(cx - 36, cy - 36, cx + 36, cy + 36, outline="#1d5780", width=2, tags="plus")
        cv.create_text(cx, cy - 2, text="+", fill="#1d5780", font=("Menlo", 48), tags="plus")
        cv.create_text(cx, cy + 64, text="Drop an image here, or click + to open", fill="#5b6072", font=("Helvetica", 15))
        cv.tag_bind("plus", "<Button-1>", lambda _: self.pick())
        self.bar.config(text="Enter: name point   Delete: remove selected   u: undo   Left/Right: switch image")

    def pick(self):
        p = filedialog.askopenfilename(title="Open image", filetypes=[("Images", " ".join("*" + e for e in EXTS))])
        if p: self.load(p)

    def step(self, d):
        if not self.im: return self.pick()
        sib = siblings(self.path)
        self.load(sib[(sib.index(self.path) + d) % len(sib)])

    def load(self, path):
        self.im = Image.open(path)
        self.path, self.out, self.pts, self.sel = path, os.path.splitext(path)[0] + "_coords.txt", [], None
        if os.path.exists(self.out):
            for line in open(self.out, encoding="utf-8"):
                f = line.rstrip("\n").split("\t")
                if len(f) == 3: self.pts.append([f[0], int(f[1]), int(f[2])])
        self.cv.config(cursor="crosshair")
        self.fname.config(state="normal"); self.fname.delete(0, "end"); self.fname.insert(0, os.path.basename(path)); self.fname.config(state="readonly")
        sib = siblings(path)
        self.nav.config(text=f"{sib.index(path) + 1} / {len(sib)}   {os.path.dirname(path)}")
        self.fit()

    def fit(self):
        """按画布当前尺寸缩放显示（Tk 只认主屏大小，所以跟窗口走）；读数总是换算回原图像素。"""
        im, cv = self.im, self.cv
        w, h = max(cv.winfo_width(), 2), max(cv.winfo_height(), 2)
        self.size = (w, h)
        self.scale = s = min(w / im.width, h / im.height)
        disp = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.LANCZOS)
        self.photo = ImageTk.PhotoImage(disp)
        cv.delete("all"); cv.create_image(0, 0, image=self.photo, anchor="nw")
        self.root.title(f"{os.path.basename(self.path)}  {im.width}x{im.height}  zoom {s:.3f}  |  {self.out}")
        self.redraw()

    def redraw(self):
        """点位、标签、右侧列表全部按 self.pts 重画，选中的用红色。"""
        cv = self.cv; cv.delete("pt"); self.lb.delete(0, "end")
        for i, (name, x, y) in enumerate(self.pts):
            c = SEL if i == self.sel else MARK
            cx, cy = x * self.scale, y * self.scale
            cv.create_oval(cx - 4, cy - 4, cx + 4, cy + 4, outline=c, width=2, tags="pt")
            cv.create_text(cx + 8, cy - 8, text=f"{name} ({x},{y})", anchor="w", fill=c, font=("Menlo", 13, "bold"), tags="pt")
            self.lb.insert("end", f"{name}  {x}  {y}")
        if self.sel is not None: self.lb.selection_set(self.sel); self.lb.see(self.sel)
        with open(self.out, "w", encoding="utf-8") as f:
            for name, x, y in self.pts: f.write(f"{name}\t{x}\t{y}\n")

    def copy_name(self):
        if not self.im: return
        self.root.clipboard_clear(); self.root.clipboard_append(os.path.basename(self.path))
        self.bar.config(text=f"Copied {os.path.basename(self.path)}")

    def rename(self):
        """双击列表行或选中的标记：在标记旁弹出预填名字的输入框。"""
        if self.im and self.sel is not None:
            name, x, y = self.pts[self.sel]
            self.name_at(None, at=(x * self.scale, y * self.scale), edit=self.sel, preset=name)

    def copy(self, all_rows=False):
        """cmd+C：选中一行就复制那行，没选就复制全部；按钮永远复制全部。格式和 txt 一样，Tab 分隔。"""
        rows = [self.pts[self.sel]] if self.sel is not None and not all_rows else self.pts
        lines = [f"{n}\t{x}\t{y}" for n, x, y in rows]
        if all_rows: lines.insert(0, os.path.basename(self.path))  # Copy all 第一行带图名
        text = "\n".join(lines)
        self.root.clipboard_clear(); self.root.clipboard_append(text)
        self.bar.config(text=f"Copied {len(rows)} rows")

    def select(self, i):
        self.sel = i; self.redraw()

    def delete(self):
        if self.im and self.sel is not None:
            name = self.pts.pop(self.sel)[0]; self.sel = None; self.redraw()
            self.bar.config(text=f"Deleted {name}   {len(self.pts)} points left")

    def undo(self):
        if self.im and self.pts:
            self.sel = len(self.pts) - 1; self.delete()

    def on_move(self, e):
        if not self.im: return
        self.last = (e.x, e.y)
        x, y = to_img(e.x, e.y, self.scale)
        px = self.im.getpixel((min(x, self.im.width - 1), min(y, self.im.height - 1)))
        self.bar.config(text=f"x={x}  y={y}    RGB={px[:3] if isinstance(px, tuple) else px}    {len(self.pts)} points")

    def on_left(self, e):
        """点到已标的点附近就选中它，否则复制坐标。"""
        if not self.im: return
        x, y = to_img(e.x, e.y, self.scale)
        near = [i for i, (_, px, py) in enumerate(self.pts) if abs(px - x) * self.scale < 10 and abs(py - y) * self.scale < 10]
        if near:
            self.select(near[0]); self.bar.config(text=f"Selected {self.pts[near[0]][0]}, press Delete to remove")
        else:
            self.select(None)
            self.root.clipboard_clear(); self.root.clipboard_append(f"{x},{y}")
            self.bar.config(text=f"Copied {x},{y}")

    def name_at(self, e, at=None, edit=None, preset=""):
        """输入框直接嵌在画布上，不弹新窗口。edit 给了下标就是改名，否则新建。"""
        if not self.im: return
        ex, ey = at or ((e.x, e.y) if e else self.last)
        x, y = self.pts[edit][1:] if edit is not None else to_img(ex, ey, self.scale)
        self.cv.delete("entry")
        ent = tk.Entry(self.cv, font=("Menlo", 14), width=18, bg="white", fg=MARK, insertbackground=MARK)
        self.cv.create_window(ex + 10, ey + 10, window=ent, anchor="nw", tags="entry")
        ent.insert(0, preset); ent.select_range(0, "end"); ent.focus_set()
        self.bar.config(text=f"{'Rename' if edit is not None else 'Name for'} ({x}, {y})? Enter to confirm, Esc to cancel")

        def done(_=None, ok=True):
            name = ent.get().strip()
            self.cv.delete("entry"); ent.destroy(); self.cv.focus_set()
            if ok and name:
                if edit is not None: self.pts[edit][0] = name
                else: self.pts.append([name, x, y]); self.sel = None
                self.redraw()
                self.bar.config(text=f"Saved {name} ({x},{y})   {len(self.pts)} points")
        ent.bind("<Return>", done)
        ent.bind("<Escape>", lambda _: done(ok=False))


def selftest():
    assert to_img(100, 50, 1.0) == (100, 50)
    assert to_img(953, 540, 0.5) == (1906, 1080)
    assert parse_drop("{/a b/c.png} /d/e.jpg /f/g.txt") == ["/a b/c.png", "/d/e.jpg"]
    print("selftest ok")


if __name__ == "__main__":
    a = sys.argv[1:]
    selftest() if a[:1] == ["--selftest"] else Picker(a[0] if a else None)
