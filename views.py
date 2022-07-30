import tkinter as tk
from tkinter import ttk
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg)
from Database import db_stock, db_candle


# 查找页面 类
class SearchFrame(tk.Frame):
    def __init__(self, root):
        super().__init__(root)
        self.name = tk.StringVar()
        self.tree_view = None

        tk.Label(self, text='查找页面').pack()

        self.table_view = tk.Frame()
        self.table_view.pack()

        self.creat_page()

    def creat_page(self):
        # 输入框
        tk.Entry(self, width=40, textvariable=self.name).pack(pady=5)

        # 搜索结果列表
        columns = ("code", "code_name")
        self.tree_view = ttk.Treeview(self, show='headings', columns=columns, height=30)
        self.tree_view.column('code', width=80, anchor='center')
        self.tree_view.column('code_name', width=160, anchor='center')
        self.tree_view.heading('code', text='股票代码')
        self.tree_view.heading('code_name', text='股票名称')
        # 绑定点击列表行事件
        self.tree_view.bind('<ButtonRelease-1>', self.select_item)
        self.tree_view.pack(fill=tk.BOTH, expand=True)

        # 查找按钮
        tk.Button(self, text='查找', command=self.recode_info).pack(pady=5)

    # 点击列表行事件
    def select_item(self, event):
        cur_item = self.tree_view.item(self.tree_view.focus())
        col = self.tree_view.identify_column(event.x)
        cur_code = cur_item['values'][0]
        cur_code_name = cur_item['values'][1]
        print('curItem = ', cur_item)
        print('col = ', col)
        print('code = ', cur_code, 'code_name = ', cur_code_name)
        db_candle.change_data(cur_code, cur_code_name)

    # 按钮点击事件: 搜索
    def recode_info(self):
        print(self.name.get())
        db_stock.change_name(self.name.get())
        self.delete_info()
        index = 0
        for row in db_stock.data:
            self.tree_view.insert("", index, value=row)

    # 列表清空函数
    def delete_info(self):
        x = self.tree_view.get_children()
        for item in x:
            self.tree_view.delete(item)


# K线视图类
class KlineFrame(tk.Frame):
    def __init__(self, root):
        super().__init__(root)
        self.day = FigureCanvasTkAgg()
        self.week = FigureCanvasTkAgg()
        self.mouth = FigureCanvasTkAgg()
        self.creat_page()

    # 生成页面
    def creat_page(self):
        tk.Button(self, width=6, text='日K', command=self.show_day).grid(row=0, column=0, padx=10)
        tk.Button(self, width=6, text='周K', command=self.show_week).grid(row=0, column=1, padx=10)
        tk.Button(self, width=6, text='月K', command=self.show_mouth).grid(row=0, column=2, padx=10)
        self.show_day()

    # 展示日线 隐藏周线和月线
    def show_day(self):
        self.day = FigureCanvasTkAgg(db_candle.creat_figure(db_candle.day), master=self)
        self.day.draw()
        self.day.get_tk_widget().grid(row=1, column=0, columnspan=3)
        self.week.get_tk_widget().grid_forget()
        self.mouth.get_tk_widget().grid_forget()

    def show_week(self):
        self.week = FigureCanvasTkAgg(db_candle.creat_figure(db_candle.week), master=self)
        self.week.draw()
        self.day.get_tk_widget().grid_forget()
        self.week.get_tk_widget().grid(row=1, column=0, columnspan=3)
        self.mouth.get_tk_widget().grid_forget()

    def show_mouth(self):
        self.mouth = FigureCanvasTkAgg(db_candle.creat_figure(db_candle.mouth), master=self)
        self.mouth.draw()
        self.day.get_tk_widget().grid_forget()
        self.week.get_tk_widget().grid_forget()
        self.mouth.get_tk_widget().grid(row=1, column=0, columnspan=3)


# 关于页面 类
class AboutFrame(tk.Frame):
    def __init__(self, root):
        super().__init__(root)
        tk.Label(self, text='关于作品： 本作品由tkinter、baostock、mpfinance制作').pack()
        tk.Label(self, text='关于作者： 电子18 谢磊').pack()


if __name__ == '__main__':
    main = tk.Tk()

    chart = tk.Frame(main)
    chart.pack()

    main.mainloop()
