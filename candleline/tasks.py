"""线程池任务：把阻塞调用移出 GUI 线程。"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, QRunnable, Signal


class Dispatcher(QObject):
    """由主线程持有的信号中枢，保证结果以排队方式回到 GUI 线程。"""

    done = Signal(int, object)
    failed = Signal(int, str)


class Worker(QRunnable):
    def __init__(
        self,
        dispatcher: Dispatcher,
        token: int,
        func: Callable[..., Any],
        *args: Any,
    ) -> None:
        super().__init__()
        self._dispatcher = dispatcher
        self._token = token
        self._func = func
        self._args = args

    def run(self) -> None:
        try:
            result = self._func(*self._args)
        except Exception as exc:  # 网络与数据异常统一交给界面提示
            self._dispatcher.failed.emit(self._token, str(exc))
        else:
            self._dispatcher.done.emit(self._token, result)
