"""界面层：查询页、K 线页、关于页。"""

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox, ttk

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

import Database


class SearchFrame(tk.Frame):
    """按名称模糊搜索股票，点击结果切换 K 线。"""

    def __init__(self, master: tk.Misc, on_select) -> None:
        super().__init__(master)
        self.on_select = on_select
        self.keyword = tk.StringVar()
        self.status = tk.StringVar(value="输入股票名称后回车或点查找")
        self._build()

    def _build(self) -> None:
        tk.Label(self, text="查找股票").pack(pady=(12, 4))
        entry = tk.Entry(self, width=40, textvariable=self.keyword)
        entry.pack(pady=4)
        entry.bind("<Return>", lambda _event: self.search())
        tk.Button(self, text="查找", command=self.search).pack(pady=4)

        columns = ("code", "code_name")
        self.tree = ttk.Treeview(self, show="headings", columns=columns, height=24)
        self.tree.heading("code", text="股票代码")
        self.tree.heading("code_name", text="股票名称")
        self.tree.column("code", width=100, anchor="center")
        self.tree.column("code_name", width=180, anchor="center")
        self.tree.bind("<ButtonRelease-1>", self._select)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=12)
        tk.Label(self, textvariable=self.status, anchor="w").pack(
            fill=tk.X, padx=12, pady=4
        )

    def search(self) -> None:
        keyword = self.keyword.get().strip()
        self._clear()
        if not keyword:
            self.status.set("请输入股票名称")
            return
        try:
            stocks = Database.search_stocks(keyword)
        except Database.DataError as exc:
            messagebox.showerror("查询失败", str(exc), parent=self)
            return
        for code, name in stocks:
            self.tree.insert("", tk.END, values=(code, name))
        self.status.set(
            f"“{keyword}” 匹配 {len(stocks)} 只股票"
            if stocks
            else f"没有匹配“{keyword}”的股票"
        )

    def _select(self, event: tk.Event) -> None:
        row = self.tree.identify_row(event.y)
        if not row:
            return
        values = self.tree.item(row, "values")
        if len(values) < 2:
            return
        self.status.set(f"已选择 {values[1]}（{values[0]}）")
        self.on_select(values[0], values[1])

    def _clear(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)


class KlineFrame(tk.Frame):
    """按日/周/月展示 K 线；网络请求放后台线程，绘图留在主线程。"""

    def __init__(self, master: tk.Misc, candle: Database.Candle) -> None:
        super().__init__(master)
        self.candle = candle
        self.freq = "d"
        self.canvas: FigureCanvasTkAgg | None = None
        self.figure = None
        self._request = 0
        self._build()

    def _build(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)
        bar = tk.Frame(self)
        bar.grid(row=0, column=0, sticky="w", padx=8, pady=6)
        for freq, label in Database.FREQ_NAMES.items():
            tk.Button(
                bar, text=label, width=6, command=lambda f=freq: self.show(f)
            ).pack(side=tk.LEFT, padx=4)
        self.status = tk.Label(self, text="", anchor="w")
        self.status.grid(row=1, column=0, sticky="ew", padx=8)
        self.holder = tk.Frame(self)
        self.holder.grid(row=2, column=0, sticky="nsew")

    def show(self, freq: str) -> None:
        self.freq = freq
        self.reload()

    def select_stock(self, code: str, name: str) -> None:
        self.candle.update(code, name)
        self.reload()

    def reload(self) -> None:
        self._request += 1
        token = self._request
        self.status.config(
            text=f"正在加载 {self.candle.name} 的{Database.FREQ_NAMES[self.freq]}…"
        )
        threading.Thread(
            target=self._fetch, args=(token, self.freq), daemon=True
        ).start()

    def _fetch(self, token: int, freq: str) -> None:
        try:
            data = self.candle.frame(freq)
        except Exception as exc:  # 网络/接口异常统一反馈到界面
            self.after(0, self._failed, token, exc)
        else:
            self.after(0, self._draw, token, freq, data)

    def _failed(self, token: int, exc: Exception) -> None:
        if token != self._request:
            return
        self.status.config(text=f"加载失败：{exc}")
        messagebox.showerror("加载失败", str(exc), parent=self)

    def _draw(self, token: int, freq: str, data) -> None:
        if token != self._request:
            return
        figure = self.candle.make_figure(data, freq)
        if self.canvas is not None:
            self.canvas.get_tk_widget().destroy()
        if self.figure is not None:
            plt.close(self.figure)
        self.figure = figure
        self.canvas = FigureCanvasTkAgg(figure, master=self.holder)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self.status.config(
            text=f"{self.candle.code} {self.candle.name} · "
            f"{Database.FREQ_NAMES[freq]} · 共 {len(data)} 根"
        )


class AboutFrame(tk.Frame):
    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master)
        tk.Label(
            self,
            text="关于作品：本作品由 tkinter、baostock、mplfinance 制作",
        ).pack(pady=20)
