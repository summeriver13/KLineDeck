import baostock as bs
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import mplfinance as mpf
import time


# 模糊搜索获取股票代码
class Stock:
    def __init__(self, name):
        self.name = name
        self.code = None
        self.code_name = None
        self.data = self.get_data()

    # 获取数据
    def get_data(self):
        lg = bs.login()

        print('login respond  error_msg:' + lg.error_msg)
        rs = bs.query_stock_basic(code_name=self.name)  # 支持模糊查询
        print('query_stock_basic respond error_code:' + rs.error_code)
        print('query_stock_basic respond  error_msg:' + rs.error_msg)
        data_list = []
        while (rs.error_code == '0') & rs.next():
            data_list.append(rs.get_row_data())
        result = pd.DataFrame(data_list, columns=rs.fields)
        result.to_csv("stock_basic.csv", encoding="gbk", index=False)
        print(result)

        bs.logout()

        # 数据处理 只保留 股票代码和股票名称两列
        code_list = pd.read_csv('stock_basic.csv', encoding="gbk", usecols=[0, 1])
        return code_list.values.tolist()

    # 搜索名称改变事件
    def change_name(self, name):
        self.name = name
        self.data = self.get_data()


# K线图视觉参数设置 调整为中国股市视觉习惯 红涨绿跌
# 设置mplfinance的蜡烛颜色，up为阳线颜色，down为阴线颜色
my_color = mpf.make_marketcolors(up='r',
                                 down='g',
                                 edge='inherit',
                                 wick='inherit',
                                 volume='inherit')
# 设置图表的背景色
my_style = mpf.make_mpf_style(marketcolors=my_color,
                              figcolor='(0.82, 0.83, 0.85)',
                              gridcolor='(0.82, 0.83, 0.85)')

# 标题字体
title_font = {'fontname': 'SimHei',
              'size': '16',
              'color': 'black',
              'weight': 'bold',
              'va': 'bottom',
              'ha': 'center'}

# 一般 标签 字体
normal_label_font = {'fontname': 'SimHei',
                     'size': '12',
                     'color': 'black',
                     'va': 'bottom',
                     'ha': 'right'}
# 大号红色字体
large_red_font = {'fontname': 'Arial',
                  'size': '16',
                  'color': 'red',
                  'weight': 'bold',
                  'va': 'bottom'}
# 小号红色字体
small_red_font = {'fontname': 'Arial',
                  'size': '12',
                  'color': 'red',
                  'weight': 'bold',
                  'va': 'bottom'}
# 小号绿色字体
small_green_font = {'fontname': 'Arial',
                    'size': '12',
                    'color': 'green',
                    'weight': 'bold',
                    'va': 'bottom'}
# 普通字体
normal_font = {'fontname': 'Arial',
               'size': '12',
               'color': 'black',
               'va': 'bottom',
               'ha': 'left'}


# k线图 类
class Candle:
    def __init__(self, code, code_name):
        self.code = code
        self.code_name = code_name
        self.start_date_day = '2020-1-01'
        self.start_date_week = '2020-1-01'
        self.start_date_mouth = '2010-1-01'
        self.end_date = time.strftime('%Y-%m-%d', time.localtime())

        self.my_style = my_style

        # k线数据 分 日 周 月
        self.day = self.get_data("d", self.start_date_day)
        self.week = self.get_data("w", self.start_date_week)
        self.mouth = self.get_data("m", self.start_date_mouth)

        self.fig = None

    # 数据更改事件
    def change_data(self, code, code_name):
        self.code = code
        self.code_name = code_name
        self.day = self.get_data("d", self.start_date_day)
        self.week = self.get_data("w", self.start_date_week)
        self.mouth = self.get_data("m", self.start_date_mouth)

    # 数据获取
    def get_data(self, fq, start_date):
        bs.login()

        rs = bs.query_history_k_data_plus(self.code,
                                          "date,code,open,high,low,close,volume,turn,pctChg",
                                          start_date=start_date, end_date=self.end_date,
                                          frequency=fq, adjustflag="3")
        data_list = []
        while (rs.error_code == '0') & rs.next():
            data_list.append(rs.get_row_data())
        result = pd.DataFrame(data_list, columns=rs.fields)
        result.to_csv("data.csv", index=False)
        print(result)

        bs.logout()

        # 数据处理 删除股票代码列
        return pd.read_csv('data.csv', index_col=0, parse_dates=True, usecols=[0, 2, 3, 4, 5, 6, 7, 8])

    # K线绘图
    def creat_figure(self, data):
        plot_data = data.iloc[-101:-1]
        last_data = plot_data.iloc[-1]
        self.fig = mpf.figure(style=my_style, figsize=(12, 8), facecolor=(0.82, 0.83, 0.85))
        ax1 = self.fig.add_axes([0.06, 0.25, 0.88, 0.60])
        ax2 = self.fig.add_axes([0.06, 0.15, 0.88, 0.10], sharex=ax1)
        ax1.set_ylabel('price')
        ax2.set_ylabel('volume')
        t1 = self.fig.text(0.50, 0.95, db_candle.code+' - '+db_candle.code_name, **title_font)
        t2 = self.fig.text(0.10, 0.90, '开盘价: ', **normal_label_font)
        t2 = self.fig.text(0.10, 0.90, f'{np.round(last_data["open"], 3)}', **small_red_font)
        t3 = self.fig.text(0.10, 0.86, '收盘价: ', **normal_label_font)
        t4 = self.fig.text(0.10, 0.86, f'{np.round(last_data["close"], 3)}', **small_green_font)
        t5 = self.fig.text(0.30, 0.90, '最高价: ', **normal_label_font)
        t6 = self.fig.text(0.30, 0.90, f'{last_data["high"]}', **small_red_font)
        t7 = self.fig.text(0.30, 0.86, '最低价: ', **normal_label_font)
        t8 = self.fig.text(0.30, 0.86, f'{last_data["low"]}', **small_green_font)
        t9 = self.fig.text(0.50, 0.90, '换手率: ', **normal_label_font)
        t10 = self.fig.text(0.50, 0.90, f'{last_data["turn"]}', **normal_font)
        t11 = self.fig.text(0.50, 0.86, '涨跌幅: ', **normal_label_font)
        t12 = self.fig.text(0.50, 0.86, f'{last_data["pctChg"]}', **normal_font)
        t13 = self.fig.text(0.70, 0.90, '成交量(万手): ', **normal_label_font)
        t14 = self.fig.text(0.70, 0.90, f'{np.round(last_data["volume"] / 10000, 3)}', **normal_font)
        mpf.plot(plot_data,
                 ax=ax1,
                 volume=ax2,
                 type='candle',
                 style=self.my_style)
        return self.fig


db_stock = Stock('特斯拉')
db_candle = Candle('sh.000001', '浦发银行')

if __name__ == '__main__':
    a = Candle('sh.000001', 'name')
