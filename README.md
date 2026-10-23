<div align="center">

# KLineDeck

**A 股 K 线工作台**

Qt + pyqtgraph 自绘蜡烛图 · Baostock 行情 · 本地缓存与按需补历史

![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![Qt](https://img.shields.io/badge/Qt-PySide6-41CD52?style=flat-square&logo=qt&logoColor=white)
![pyqtgraph](https://img.shields.io/badge/pyqtgraph-0.14-1f6feb?style=flat-square)
![Baostock](https://img.shields.io/badge/Data-Baostock-0ea5e9?style=flat-square)
[![License](https://img.shields.io/badge/License-MIT-2ea44f?style=flat-square)](LICENSE)

</div>

<p align="center">
  <img src="docs/preview.png" alt="KLineDeck 界面：上证指数日 K、均线、BOLL、MACD 和自选列表" width="960">
  <br>
  <sub>上证指数 · 1 年视图 · MA / BOLL / MACD / 自选</sub>
</p>

KLineDeck 是一个面向 A 股的桌面行情终端。界面用 Qt 原生控件与 pyqtgraph 绘制，不套 WebView；行情来自 Baostock，打开即用，不依赖浏览器或前端服务。

## 为什么是 KLineDeck

- **原生桌面体验**：滚轮缩放、拖拽平移、跨价格 / 成交量 / 副图联动的十字光标，操作接近券商客户端。
- **为 A 股工作流设计**：日 / 周 / 月 K、三种复权、区间视图、自选股和本地 A 股目录搜索都在一个窗口内完成。
- **加载不打断交互**：网络请求走后台线程；首屏只取最近 3 年，接近左边界时自动补更早历史，完整历史按需补全。
- **指标口径可验证**：SMA、EMA、MACD、KDJ、RSI、BOLL 为纯 numpy 实现，配有公式回归测试。
- **数据本地优先**：K 线以 npz 缓存，搜索读取随包目录快照，缓存命中时二次打开接近瞬时。

## 功能

| 分类 | 能力 |
| --- | --- |
| 行情 | 日 K / 周 K / 月 K；前复权 / 后复权 / 不复权 |
| 视图 | 1 月 / 3 月 / 6 月 / 1 年 / 3 年 / 全部；滚轮缩放、拖拽平移、Y 轴自适应 |
| 主图 | MA5 / MA10 / MA20 / MA60、BOLL(20, 2)、最新价线 |
| 成交量 | 成交量柱、MA5 / MA10，支持缺失值 |
| 副图 | MACD(12, 26, 9)、KDJ(9, 3, 3)、RSI(6, 12, 24)，可切换 |
| 交互 | 跨面板十字光标，显示 OHLC、涨跌幅、成交量、换手率和指标读数 |
| 搜索 | 本地 A 股与指数目录，毫秒级返回；港股、美股不在支持范围 |
| 自选 | 行情头部 ★ 一键加入 / 移出；双击加载、右键管理；本地持久化 |
| 输出 | 当前图表导出 PNG |

全历史视图会自动切换为收盘线，避免上千根蜡烛挤成一团；缩回可见区间后恢复蜡烛图。

## 快速开始

需要 Python 3.12+ 与 [uv](https://docs.astral.sh/uv/)。

```bash
git clone https://github.com/summeriver13/KLineDeck.git
cd KLineDeck
uv sync
uv run python main.py
```

首次查询需要联网，之后走本地缓存。Baostock 免费，无需 token。

## 数据与缓存

Windows 下路径如下；Linux / macOS 使用系统配置与缓存目录。

| 项目 | 位置 / 说明 |
| --- | --- |
| 自选股 | `%LOCALAPPDATA%/KLineDeck/KLineDeck/watchlist.json` |
| K 线缓存 | `%LOCALAPPDATA%/KLineDeck/cache/<数据源>/` |
| 缓存目录覆盖 | 环境变量 `KLINEDECK_CACHE_DIR` |
| 刷新策略 | 6 小时 TTL；过期后取最后 10 天重叠段增量刷新；复权基准变化时整段重取 |
| 历史补全 | 接近左边界时每次向前补约 2 年；「全部」按需补到 2010 年起的日线 |

缓存按数据源隔离。旧版 CandleLine 的缓存与自选会在首次启动时自动复制到新目录。

## 技术指标

| 指标 | 参数 | 口径 |
| --- | --- | --- |
| MA | 5 / 10 / 20 / 60 | SMA |
| BOLL | 20, 2 | 中轨 SMA(20)，上下轨 ±2 倍总体标准差 |
| MACD | 12 / 26 / 9 | 柱按国内软件惯例取 `2 * (DIF - DEA)` |
| KDJ | 9 / 3 / 3 | K / D 初值 50；最高价等于最低价时 RSV 取 50 |
| RSI | 6 / 12 / 24 | Wilder 平滑 |

## 性能

| 场景 | 实测 |
| --- | --- |
| 首次加载最近 3 年 | 0.8–8.5 s（Baostock 波动较大） |
| 二次打开（缓存命中） | 约 0.01 s |
| 缓存过期后的增量刷新 | 约 0.06 s（无新 K 线时） |
| 首次补全 2010 年起的全部日线 | 6–40 s |
| 全部历史二次打开 | 约 0.01 s |
| 4078 根全量指标计算 | 约 26 ms（一次性） |

周 / 月线数据量小，一次取全量，首次约 1 s。

<details>
<summary><strong>模块结构</strong>（点击展开）</summary>

| 路径 | 职责 |
| --- | --- |
| `main.py` | 入口：QApplication、主题、主窗口 |
| `klinedeck/models.py` | `Stock` / `Bars` / `DataError` |
| `klinedeck/data.py` | 数据源调度、缓存与增量刷新 |
| `klinedeck/sources/base.py` | `MarketDataSource` 接口 |
| `klinedeck/sources/baostock_source.py` | Baostock 会话、搜索与复权 K 线解析 |
| `klinedeck/cache.py` | npz 缓存、增量合并、复权因子校验 |
| `klinedeck/chart.py` | K 线控件：价格、成交量、副图、十字光标、缩放 |
| `klinedeck/chart_view.py` | 区间映射、视口保持与补历史触发 |
| `klinedeck/header.py` | 名称、代码、最新价与涨跌 |
| `klinedeck/stock_directory.py` | 本地 A 股 / 指数目录搜索 |
| `klinedeck/stock_directory.csv` | 目录快照（约 5500 条） |
| `klinedeck/items.py` | 蜡烛图元、日期轴、均线计算 |
| `klinedeck/indicators.py` | SMA / EMA / MACD / KDJ / RSI / BOLL 计算 |
| `klinedeck/indicator_panel.py` | MACD / KDJ / RSI 副图绘制与读数 |
| `klinedeck/overlays.py` | BOLL、成交量均线、最新价线 |
| `klinedeck/crosshair.py` | 跨价格 / 成交量 / 副图的十字光标 |
| `klinedeck/info.py` | OHLC、均线与指标信息栏 |
| `klinedeck/sidebar.py` | 搜索与自选 |
| `klinedeck/toolbar.py` | 周期、复权、区间、叠加指标与导出 |
| `klinedeck/window.py` | 主窗口、异步加载、完整历史补全与向左补历史 |
| `klinedeck/window_layout.py` | 中央布局与状态栏 |
| `klinedeck/theme.py` | 配色与 QSS |
| `tests/test_indicators.py` | 指标公式回归测试 |
| `tests/test_data.py` | 向前补历史、缓存合并与本地目录测试 |

</details>

## 扩展数据源

默认使用 Baostock。新增数据源只需实现 `MarketDataSource`，并在创建窗口前注册：

```python
from klinedeck import data
from klinedeck.models import Bars, Stock


class MySource:
    name = "my"

    def full_start(self, freq: str) -> str:
        ...

    def search(self, keyword: str) -> list[Stock]:
        ...

    def fetch(
        self,
        code: str,
        freq: str,
        adjust: str,
        is_index: bool,
        start: str,
        end: str | None = None,
    ) -> Bars:
        ...


data.set_source(MySource())
```

搜索与 K 线都会走同一数据源；缓存按 `name` 隔离，不会与 Baostock 的缓存混用。

## 测试

```bash
uv run python -m unittest discover -s tests -v
```

覆盖指标公式、向前补历史、缓存合并与本地目录搜索。

## 说明

- 搜索使用随包附带的本地 A 股目录快照，输入后立即返回；腾讯等港股、美股不在目录中，会直接提示无匹配，不会等待在线查询。
- 向左拖动接近缓存起点时会自动向前补约 2 年日线；补齐后按完整序列重算均线与指标，视口保持原日期区间。
- 成交量缺失按 0 处理，成交量均线不会因单日缺数中断。
- 默认前复权；周 / 月线没有 `preclose` 字段，涨跌额按上一周期收盘价计算。
- 数据仅供学习研究，不构成投资建议。

## License

[MIT](LICENSE) © 2022 summeriver
