"""流式输出过滤：隐藏 L2 内部独白与 DSML 工具泄漏。"""

from __future__ import annotations

from config.agent_mode import is_router_agent

_DSML_OPEN_MARKERS = (
    "<｜｜DSML｜｜",
    "<||DSML||",
)
_DSML_CLOSE_MARKERS = (
    "</｜｜DSML｜｜tool_calls>",
    "</||DSML||tool_calls>",
)
_MONOLOGUE_PREFIXES = tuple(
    prefix.casefold()
    for prefix in (
        "I need to",
        "Let me",
        "Now let me",
        "I'll ",
        "I will ",
        "I'm going to",
        "handle this docx",
    )
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
        if is_specialist_agent(agent_name):
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
        if self._specialist_active:
            return None
        if not is_router_agent(self._agent_name):
            return None
        cleaned = self._sanitizer.feed(delta)
        if cleaned and _is_leakage(cleaned):
            return None
        return cleaned or None

    def flush(self) -> str | None:
        if self._specialist_active or not is_router_agent(self._agent_name):
            return None
        cleaned = self._sanitizer.flush()
        if cleaned and _is_leakage(cleaned):
            return None
        return cleaned or None


def _is_leakage(text: str) -> bool:
    if any(marker.casefold() in text.casefold() for marker in _DSML_OPEN_MARKERS):
        return True
    if "transfer_to_" in text or "invoke name=" in text:
        return True
    if "｜DSML｜" in text:
        return True
    lowered = text.lstrip().casefold()
    if any(lowered.startswith(prefix) for prefix in _MONOLOGUE_PREFIXES):
        return True
    return False


class DeltaSanitizer:
    """Strip control blocks and monologue lines across arbitrary chunk boundaries."""

    def __init__(self) -> None:
        self._control_pending = ""
        self._in_control_block = False
        self._line_mode = "checking"
        self._line_prefix = ""

    def feed(self, chunk: str) -> str:
        visible = self._strip_control_blocks(chunk, final=False)
        return self._strip_monologue_lines(visible, final=False)

    def flush(self) -> str:
        visible = self._strip_control_blocks("", final=True)
        return self._strip_monologue_lines(visible, final=True)

    def _strip_control_blocks(self, chunk: str, *, final: bool) -> str:
        text = self._control_pending + chunk
        self._control_pending = ""
        output: list[str] = []

        while text:
            if self._in_control_block:
                found = _first_marker(text, _DSML_CLOSE_MARKERS)
                if found is None:
                    if not final:
                        keep = _marker_prefix_length(text, _DSML_CLOSE_MARKERS)
                        if keep:
                            self._control_pending = text[-keep:]
                    return "".join(output)
                index, marker = found
                text = text[index + len(marker) :]
                self._in_control_block = False
                continue

            found = _first_marker(text, _DSML_OPEN_MARKERS)
            if found is not None:
                index, marker = found
                output.append(text[:index])
                text = text[index + len(marker) :]
                self._in_control_block = True
                continue

            keep = 0 if final else _marker_prefix_length(text, _DSML_OPEN_MARKERS)
            visible_end = len(text) - keep
            output.append(text[:visible_end])
            self._control_pending = text[visible_end:]
            break

        if final:
            self._control_pending = ""
        return "".join(output)

    def _strip_monologue_lines(self, text: str, *, final: bool) -> str:
        output: list[str] = []
        for char in text:
            if self._line_mode == "visible":
                output.append(char)
                if char == "\n":
                    self._line_mode = "checking"
                continue

            if self._line_mode == "hidden":
                if char == "\n":
                    output.append(char)
                    self._line_mode = "checking"
                continue

            self._line_prefix += char
            candidate = self._line_prefix.lstrip().casefold()
            if char == "\n":
                output.append(self._line_prefix)
                self._line_prefix = ""
                self._line_mode = "checking"
            elif any(candidate.startswith(prefix) for prefix in _MONOLOGUE_PREFIXES):
                self._line_prefix = ""
                self._line_mode = "hidden"
            elif any(prefix.startswith(candidate) for prefix in _MONOLOGUE_PREFIXES):
                continue
            else:
                output.append(self._line_prefix)
                self._line_prefix = ""
                self._line_mode = "visible"

        if final:
            if self._line_mode == "checking":
                output.append(self._line_prefix)
            self._line_prefix = ""
            self._line_mode = "checking"
        return "".join(output)


def _first_marker(text: str, markers: tuple[str, ...]) -> tuple[int, str] | None:
    matches = ((text.find(marker), marker) for marker in markers)
    found = [(index, marker) for index, marker in matches if index >= 0]
    return min(found, key=lambda item: item[0]) if found else None


def _marker_prefix_length(text: str, markers: tuple[str, ...]) -> int:
    max_size = min(len(text), max(len(marker) for marker in markers) - 1)
    for size in range(max_size, 0, -1):
        suffix = text[-size:]
        if any(marker.startswith(suffix) for marker in markers):
            return size
    return 0
