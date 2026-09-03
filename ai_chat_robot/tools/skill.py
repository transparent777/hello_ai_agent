"""Skills 工具：列出与阅读 SKILL.md。"""

from __future__ import annotations

from agents import function_tool

from config.skills import SKILLS_ROOT


def _skill_path(skill_name: str) -> str:
    return skill_name.strip().strip("/").replace("\\", "/")


@function_tool
def list_skills() -> str:
    """列出可用的 Skill 名称与简介（YAML frontmatter 中的 description）。"""
    if not SKILLS_ROOT.is_dir():
        return "暂无 Skills 目录。"
    lines: list[str] = []
    for skill_dir in sorted(SKILLS_ROOT.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.is_file():
            continue
        text = skill_file.read_text(encoding="utf-8", errors="replace")
        desc = ""
        if text.startswith("---"):
            end = text.find("---", 3)
            if end > 0:
                for row in text[3:end].splitlines():
                    if row.strip().lower().startswith("description:"):
                        desc = row.split(":", 1)[1].strip()
                        break
        lines.append(f"- **{skill_dir.name}**：{desc or '（无简介）'}")
    if not lines:
        return "Skills 目录为空。"
    return "可用 Skills：\n" + "\n".join(lines)


@function_tool
def read_skill(skill_name: str) -> str:
    """读取指定 Skill 的完整 SKILL.md 内容。例如 output-defaults、export-formats、writing-style。"""
    name = _skill_path(skill_name)
    path = SKILLS_ROOT / name / "SKILL.md"
    if not path.is_file():
        return f"未找到 Skill：{skill_name}。请先用 list_skills 查看可用名称。"
    return path.read_text(encoding="utf-8", errors="replace")
