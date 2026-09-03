"""流式输出过滤：隐藏 L2 内部独白与 DSML 工具泄漏。"""

from __future__ import annotations

import re

from config.agent_mode import is_router_agent

_DSML_BLOCK = re.compile(
    r"<｜｜DSML｜｜[\s\S]*?(?:</｜｜DSML｜｜tool_calls>|$)",
    re.IGNORECASE,
)
_DSML_OPEN = re.compile(r"<｜｜DSML｜｜", re.IGNORECASE)
_ENGLISH_MONOLOGUE = re.compile(
    r"(?:^|\n)(?:I need to|Let me|Now let me|I'll |I will |I'm going to)[^\n]*",
    re.IGNORECASE,
)
_ENGLISH_CHUNK = re.compile(
    r"(I need to|Let me |Now let me|I'll |I will |I'm going to|handle this docx)",
    re.IGNORECASE,
)

_ROUTER_NAMES = frozenset({"workspace_router", "customer_service_router"})


def normalize_handoff_target(target: str) -> str:
    return target.removeprefix("transfer_to_")


def is_specialist_agent(agent_name: str) -> bool:
    name = normalize_handoff_target(agent_name)
    return name.endswith("_specialist")


class StreamGate:
    """按 handoff / 当前 Agent 过滤用户可见流式 token。"""

    def __init__(self, *, deliverable_task: bool) -> None:
        self.deliverable_task = deliverable_task
        self._agent_name = "workspace_router"
        self._specialist_active = False
        self._sanitizer = DeltaSanitizer()

    def set_agent(self, agent_name: str) -> None:
        self._agent_name = agent_name
        if self.deliverable_task and is_specialist_agent(agent_name):
            self._specialist_active = True
        elif is_router_agent(agent_name):
            self._specialist_active = False

    def note_handoff(self, target: str) -> None:
        name = normalize_handoff_target(target)
        if name in _ROUTER_NAMES:
            self._specialist_active = False
        elif is_specialist_agent(name) or name.endswith("_specialist"):
            self._specialist_active = True

    def emit(self, delta: str) -> str | None:
        if not delta:
            return None
        if _is_leakage(delta):
            return None
        if self.deliverable_task and self._specialist_active:
            return None
        if self.deliverable_task and not is_router_agent(self._agent_name):
            return None
        cleaned = self._sanitizer.feed(delta)
        if cleaned and _is_leakage(cleaned):
            return None
        return cleaned or None

    def flush(self) -> str | None:
        cleaned = self._sanitizer.flush()
        if cleaned and _is_leakage(cleaned):
            return None
        return cleaned or None


def _is_leakage(text: str) -> bool:
    if _DSML_OPEN.search(text):
        return True
    if "transfer_to_" in text or "invoke name=" in text:
        return True
    if "｜DSML｜" in text:
        return True
    if _ENGLISH_CHUNK.search(text):
        return True
    return False


class DeltaSanitizer:
    """增量剔除 DSML / 英文独白片段。"""

    def __init__(self) -> None:
        self._pending = ""

    def feed(self, chunk: str) -> str:
        self._pending += chunk
        return self._drain(allow_partial=False)

    def flush(self) -> str:
        return self._drain(allow_partial=True)

    def _drain(self, *, allow_partial: bool) -> str:
        text = self._pending
        if not text:
            return ""

        text = _DSML_BLOCK.sub("", text)
        text = _ENGLISH_MONOLOGUE.sub("", text)

        if _DSML_OPEN.search(text):
            cut = _DSML_OPEN.search(text)
            if cut:
                self._pending = text[cut.start() :]
                emitted = text[: cut.start()]
                return emitted if allow_partial or not self._pending else emitted
            if not allow_partial:
                self._pending = text
                return ""
            self._pending = ""
            return ""

        self._pending = ""
        return text
