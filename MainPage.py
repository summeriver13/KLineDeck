"""主窗口：菜单切换查询页、K 线页和关于页。"""

from __future__ import annotations

import tkinter as tk

import Database
import views


class MainPage:
    def __init__(self, master: tk.Tk) -> None:
        self.root = master
        self.root.title("A股K线图查询")
        self.root.geometry("1280x800")

        self.candle = Database.Candle("sh.000001", "上证指数")
        self.about_frame = views.AboutFrame(self.root)
        self.kline_frame = views.KlineFrame(self.root, self.candle)
        self.search_frame = views.SearchFrame(self.root, self.kline_frame.select_stock)
        self._build_menu()
        self.show_kline()
        self.kline_frame.show("d")

    def _build_menu(self) -> None:
        menubar = tk.Menu(self.root)
        menubar.add_command(label="查询", command=self.show_search)
        menubar.add_command(label="K线", command=self.show_kline)
        menubar.add_command(label="关于", command=self.show_about)
        self.root["menu"] = menubar

    def _hide_all(self) -> None:
        for frame in (self.search_frame, self.kline_frame, self.about_frame):
            frame.pack_forget()

    def show_search(self) -> None:
        self._hide_all()
        self.search_frame.pack(fill=tk.BOTH, expand=True)

    def show_kline(self) -> None:
        self._hide_all()
        self.kline_frame.pack(fill=tk.BOTH, expand=True)

    def show_about(self) -> None:
        self._hide_all()
        self.about_frame.pack(fill=tk.BOTH, expand=True)


if __name__ == "__main__":
    root = tk.Tk()
    MainPage(root)
    root.mainloop()
