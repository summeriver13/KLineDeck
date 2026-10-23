# CandleLine

A 股 K 线终端：Qt + pyqtgraph 自绘蜡烛图，行情来自 Baostock。

![界面](docs/preview.png)

## 功能

- 日 / 周 / 月 K，前复权、后复权、不复权切换
- 1 月 / 3 月 / 6 月 / 1 年 / 3 年 / 全部区间；滚轮缩放、拖拽平移
- 十字光标：OHLC、涨跌幅、成交量、换手率、MA 值实时浮层
- MA5 / MA10 / MA20 / MA60，成交量面板，Y 轴随可见区间自适应
- 股票与指数搜索、自选股持久化、导出 PNG
- 深色主题、高 DPI、日期轴随缩放切换粒度

## 运行

需要 Python 3.12+ 与 [uv](https://docs.astral.sh/uv/)。

```bash
uv sync
uv run python main.py
```

首次查询需要联网。Baostock 免费、无需 token。自选股保存在系统配置目录，Windows 下是
`%APPDATA%/CandleLine/CandleLine/watchlist.json`。

## 结构

| 路径 | 职责 |
| --- | --- |
| `main.py` | 入口：QApplication、主题、主窗口 |
| `candleline/data.py` | Baostock 查询、复权 K 线解析 |
| `candleline/chart.py` | K 线控件：蜡烛、成交量、均线、十字光标、缩放 |
| `candleline/items.py` | 蜡烛图元、日期轴、均线计算 |
| `candleline/sidebar.py` | 搜索与自选 |
| `candleline/window.py` | 主窗口、工具栏、异步加载 |
| `candleline/theme.py` | 配色与 QSS |

## 说明

- 数据仅供学习研究，不构成投资建议。
- 默认前复权。周 / 月线没有 `preclose` 字段，涨跌额按上一周期收盘价计算。
