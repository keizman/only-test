#!/usr/bin/env python3
"""
Only-Test Reporting Helpers
===========================
提供轻量的报告联动能力（预留 Allure 集成位）。
- 如果未安装 allure-pytest，则降级为空操作。
- 建议在执行器中包装每一步执行，自动附加 chain 中的证据。
"""
from contextlib import contextmanager
from typing import Optional

try:
    import allure  # type: ignore
except Exception:  # allure 不存在时降级
    allure = None


@contextmanager
def step(title: str):
    """兼容的 step 上下文管理器。优先使用 allure.step，否则降级为空操作。"""
    if allure is not None:
        with allure.step(title):  # type: ignore
            yield
    else:
        # 降级：直接执行，不做报告
        yield


def attach_text(name: str, text: str) -> None:
    """附加文本到报告（降级时无操作）。"""
    if allure is not None:
        allure.attach(text, name=name, attachment_type=getattr(allure.attachment_type, 'TEXT', None))  # type: ignore


def attach_file(path: str, name: Optional[str] = None) -> None:
    """附加文件到报告（降级时无操作）。"""
    if allure is not None:
        allure.attach.file(path, name or path)

