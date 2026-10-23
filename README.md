# CandleLine

基于 `baostock` + `mplfinance` + `tkinter` 的 A 股 K 线图。

## 运行

需要 Python 3.12+ 与 [uv](https://docs.astral.sh/uv/)。

```bash
uv sync
uv run python MainPage.py
```

- 查询页：输入股票名称模糊匹配在市 A 股，点击结果切换 K 线
- K 线页：日/周/月切换，数据按周期从 Baostock 按需拉取，首次需要联网
- 红涨绿跌；成交量单位为万手（1 万手 = 100 万股）
