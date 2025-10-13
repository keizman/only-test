#!/usr/bin/env python3
"""
Only-Test Prompt Builder (Minimal)
- Lightweight section-based prompt assembler inspired by Parlant's PromptBuilder
- Keeps existing prompt modules intact; this is additive and optional

Usage example:
    from only_test.templates.prompt_builder import OnlyTestPromptBuilder, SectionStatus
    builder = OnlyTestPromptBuilder()
    builder.add_section(
        name="core_step",
        template=core_prompt_text,
        status=SectionStatus.ACTIVE,
    )
    if repair_text:
        builder.add_section(
            name="repair",
            template=repair_text,
            status=SectionStatus.ACTIVE,
        )
    prompt = builder.build()
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum, auto
from io import StringIO
from typing import Any, Optional


class SectionStatus(Enum):
    ACTIVE = auto()
    PASSIVE = auto()
    NONE = auto()


@dataclass(frozen=True)
class PromptSection:
    template: str
    props: dict[str, Any]
    status: Optional[SectionStatus]


class OnlyTestPromptBuilder:
    def __init__(self) -> None:
        self._sections: list[tuple[str, PromptSection]] = []

    def add_section(
        self,
        name: str,
        template: str,
        props: dict[str, Any] | None = None,
        status: Optional[SectionStatus] = None,
    ) -> "OnlyTestPromptBuilder":
        section = PromptSection(
            template=template,
            props=props or {},
            status=status,
        )
        self._sections.append((name, section))
        return self

    def edit_section(self, name: str, template: Optional[str] = None, props: Optional[dict[str, Any]] = None, status: Optional[SectionStatus] = None) -> "OnlyTestPromptBuilder":
        for idx, (n, sec) in enumerate(self._sections):
            if n == name:
                self._sections[idx] = (
                    n,
                    PromptSection(
                        template=template if template is not None else sec.template,
                        props=props if props is not None else sec.props,
                        status=status if status is not None else sec.status,
                    ),
                )
                break
        return self

    def build(self) -> str:
        buf = StringIO()
        for name, section in self._sections:
            try:
                buf.write(section.template.format(**section.props))
            except Exception:
                # Fallback to raw template if formatting fails
                buf.write(section.template)
            buf.write("\n\n")
        return buf.getvalue().strip()
