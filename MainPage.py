"""
项目分为三部分 主页 子页视图 数据库
"""
import tkinter as tk
import views


# 主页类
class MainPage:
    def __init__(self, master: tk.Tk):
        self.about_frame = None
        self.kline_frame = None
        self.search_frame = None

        self.root = master
        self.root.title('证券可视化平台')
        self.root.geometry('1280x800')
        self.creat_page()

    # 生成软件页面
    def creat_page(self):
        self.about_frame = views.AboutFrame(self.root)
        self.kline_frame = views.KlineFrame(self.root)
        self.search_frame = views.SearchFrame(self.root)

        # 菜单栏
        menubar = tk.Menu(self.root)
        menubar.add_command(label='查询', command=self.show_search)
        menubar.add_command(label='K线', command=self.show_kline)
        menubar.add_command(label='关于', command=self.show_about)
        self.root['menu'] = menubar

    # 页面展示
    def show_search(self):
        # 展示其中一个页面时隐藏其它的页面
        self.search_frame.pack()
        self.kline_frame.pack_forget()
        self.about_frame.pack_forget()

    def show_kline(self):
        self.search_frame.pack_forget()
        self.kline_frame.pack()
        self.about_frame.pack_forget()

    def show_about(self):
        self.search_frame.pack_forget()
        self.kline_frame.pack_forget()
        self.about_frame.pack()


if __name__ == '__main__':
    root = tk.Tk()
    MainPage(root)
    root.mainloop()
