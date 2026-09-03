"""层级 ReAct 步骤：从 stream_events 解析为可折叠展示的摘要。"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any

from agents import Agent
from agents.stream_events import AgentUpdatedStreamEvent, RunItemStreamEvent, StreamEvent
from agents.items import ToolCallItem, ToolCallOutputItem

from config.agent_mode import react_layer_label


@dataclass
class ReactStep:
    layer: str
    agent: str
    kind: str
    label: str
    detail: str = ""

    def to_dict(self) -> dict[str, str]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ReactStep:
        return cls(
            layer=str(data.get("layer", "L?")),
            agent=str(data.get("agent", "")),
            kind=str(data.get("kind", "")),
            label=str(data.get("label", "")),
            detail=str(data.get("detail", "")),
        )


class ReactStepCollector:
    """收集单轮对话中的 ReAct 步骤。"""

    def __init__(self, *, initial_agent: str = "workspace_router") -> None:
        self._agent_name = initial_agent
        self.steps: list[ReactStep] = []

    def set_agent(self, agent_name: str) -> None:
        self._agent_name = agent_name

    def add(self, step: ReactStep) -> None:
        self.steps.append(step)

    def consume(self, event: StreamEvent) -> ReactStep | None:
        if isinstance(event, AgentUpdatedStreamEvent):
            name = getattr(event.new_agent, "name", "unknown")
            self._agent_name = name
            step = ReactStep(
                layer=react_layer_label(name),
                agent=name,
                kind="agent_switch",
                label=f"→ {name}",
                detail=f"切换到专员 {name}",
            )
            self.add(step)
            return step

        if not isinstance(event, RunItemStreamEvent):
            return None

        item = event.item
        layer = react_layer_label(self._agent_name)

        if event.name == "handoff_requested" or event.name == "handoff_occured":
            target = _handoff_target(item)
            step = ReactStep(
                layer=layer,
                agent=self._agent_name,
                kind="handoff",
                label=f"转接 → {target}",
                detail=f"handoff 至 {target}",
            )
            self.add(step)
            return step

        if event.name == "tool_called" and isinstance(item, ToolCallItem):
            args_preview = _truncate(_format_tool_args(item), 240)
            step = ReactStep(
                layer=layer,
                agent=self._agent_name,
                kind="action",
                label=f"调用 {item.tool_name}",
                detail=args_preview,
            )
            self.add(step)
            return step

        if event.name == "tool_output" and isinstance(item, ToolCallOutputItem):
            preview = _truncate(str(item.output or ""), 400)
            step = ReactStep(
                layer=layer,
                agent=self._agent_name,
                kind="observation",
                label="工具返回",
                detail=preview,
            )
            self.add(step)
            return step

        return None


def _handoff_target(item: Any) -> str:
    target = getattr(item, "target_agent", None)
    if target is not None:
        return getattr(target, "name", "specialist")
    raw = getattr(item, "raw_item", None)
    if raw is not None and hasattr(raw, "name"):
        return str(raw.name)
    return getattr(item, "agent_name", "specialist")


def _format_tool_args(item: ToolCallItem) -> str:
    raw = getattr(item, "raw_item", None)
    if raw is None:
        return ""
    try:
        if hasattr(raw, "arguments"):
            return str(raw.arguments)
        return json.dumps(raw, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return str(raw)


def _truncate(text: str, limit: int) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def compact_summary(steps: list[ReactStep], *, max_items: int = 4) -> str:
    """终端单行缩写摘要。"""
    if not steps:
        return ""
    labels = [f"{s.layer}:{s.label}" for s in steps[:max_items]]
    extra = len(steps) - max_items
    if extra > 0:
        labels.append(f"+{extra}")
    return " · ".join(labels)


def steps_to_json(steps: list[ReactStep]) -> str:
    return json.dumps([s.to_dict() for s in steps], ensure_ascii=False)


def steps_from_json(raw: str | None) -> list[ReactStep]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    return [ReactStep.from_dict(item) for item in data if isinstance(item, dict)]
