"""`lem render` static HTML generator."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader


def _md_to_html(text: str) -> str:
    """Minimal markdown → HTML renderer. No external deps required.

    WHY custom: avoids adding markdown-it-py dep for the small subset of markdown
    features used in lem deliverables (headings, bold, italic, lists, code).
    """
    lines = text.splitlines()
    out: list[str] = []
    i = 0
    in_ul = False
    in_ol = False
    in_pre = False

    def close_lists() -> None:
        nonlocal in_ul, in_ol
        if in_ul:
            out.append("</ul>")
            in_ul = False
        if in_ol:
            out.append("</ol>")
            in_ol = False

    while i < len(lines):
        line = lines[i]

        if line.startswith("```"):
            close_lists()
            if not in_pre:
                out.append("<pre><code>")
                in_pre = True
            else:
                out.append("</code></pre>")
                in_pre = False
            i += 1
            continue

        if in_pre:
            out.append(_escape(line))
            i += 1
            continue

        if not line.strip():
            close_lists()
            i += 1
            continue

        if line.startswith("### "):
            close_lists()
            out.append(f"<h3>{_inline(line[4:])}</h3>")
        elif line.startswith("## "):
            close_lists()
            out.append(f"<h2>{_inline(line[3:])}</h2>")
        elif line.startswith("# "):
            close_lists()
            out.append(f"<h1>{_inline(line[2:])}</h1>")
        elif line.startswith("> "):
            close_lists()
            out.append(f"<blockquote><p>{_inline(line[2:])}</p></blockquote>")
        elif re.match(r"^\d+\. ", line):
            if in_ul:
                close_lists()
            if not in_ol:
                out.append("<ol>")
                in_ol = True
            content = re.sub(r"^\d+\. ", "", line)
            out.append(f"<li>{_inline(content)}</li>")
        elif line.startswith("- ") or line.startswith("* "):
            if in_ol:
                close_lists()
            if not in_ul:
                out.append("<ul>")
                in_ul = True
            out.append(f"<li>{_inline(line[2:])}</li>")
        else:
            close_lists()
            out.append(f"<p>{_inline(line)}</p>")

        i += 1

    close_lists()
    if in_pre:
        out.append("</code></pre>")

    return "\n".join(out)


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _inline(text: str) -> str:
    text = _escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    text = re.sub(r"`(.+?)`", r"<code>\1</code>", text)
    text = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', text)
    return text


def _fmt_duration(seconds: float) -> str:
    s = int(seconds)
    if s < 60:
        return f"{s}s"
    m, s = divmod(s, 60)
    if m < 60:
        return f"{m}m {s}s"
    h, m = divmod(m, 60)
    return f"{h}h {m}m"


def _bar_chart_svg(
    labels: list[str], values: list[float], color: str = "#6c8ebf"
) -> str:
    if not values or max(values) == 0:
        return '<svg class="chart"></svg>'
    max_val = max(values)
    width = 320
    bar_area_h = 100
    bar_area_y = 10
    n = len(values)
    bar_w = max(4, (width - 20) // n - 4)
    spacing = (width - 20) // n

    svg_open = '<svg class="chart" viewBox="0 0 320 140" xmlns="http://www.w3.org/2000/svg">'
    parts = [svg_open]
    for idx, (label, val) in enumerate(zip(labels, values)):
        x = 10 + idx * spacing
        bar_h = int(bar_area_h * val / max_val) if max_val else 0
        y = bar_area_y + bar_area_h - bar_h
        parts.append(
            f'<rect x="{x}" y="{y}" width="{bar_w}"'
            f' height="{bar_h}" fill="{color}" rx="2"/>'
        )
        short = label[:6]
        tx = x + bar_w // 2
        parts.append(
            f'<text x="{tx}" y="125" text-anchor="middle"'
            f' fill="#8892a4" font-size="9">{_escape(short)}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


def _load_phase_costs(workspace_path: Path) -> dict[str, dict[str, float]]:
    from lem.state.cost import read_cost
    phase_data: dict[str, dict[str, float]] = {}
    for event in read_cost(workspace_path):
        entry = phase_data.setdefault(event.phase, {"cost": 0.0, "duration": 0.0})
        entry["cost"] += event.cost_usd
        entry["duration"] += event.duration_s
    return phase_data


def _deliverable_list(workspace_path: Path) -> list[dict[str, Any]]:
    deliverables_dir = workspace_path / "deliverables"
    known = [
        "executive-summary.md",
        "mvp-plan.md",
        "risks-and-rejected-paths.md",
        "investor-onepager.md",
        "roadmap.md",
        "tech-stack.md",
    ]
    result: list[dict[str, Any]] = []
    for name in known:
        path = deliverables_dir / name
        result.append({"name": name, "exists": path.exists()})
    return result


def generate_report(workspace_path: Path, output_path: Path) -> None:
    from lem.state.run_state import read_state

    state = read_state(workspace_path)

    executive_summary_path = workspace_path / "deliverables" / "executive-summary.md"
    executive_summary_html = ""
    if executive_summary_path.exists():
        md = executive_summary_path.read_text(encoding="utf-8")
        executive_summary_html = _md_to_html(md)

    phase_costs = _load_phase_costs(workspace_path)
    phases = sorted(phase_costs.keys())
    cost_values = [phase_costs[p]["cost"] for p in phases]
    duration_values = [phase_costs[p]["duration"] for p in phases]

    cost_chart_svg = _bar_chart_svg(phases, cost_values, "#6c8ebf")
    duration_chart_svg = _bar_chart_svg(phases, duration_values, "#4caf50")

    duration_s = state.last_event_at - state.started_at
    started_dt = datetime.fromtimestamp(state.started_at, tz=timezone.utc)

    template_dir = Path(__file__).parent
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=False,
    )
    template = env.get_template("template.html")

    html = template.render(
        run_id=state.run_id,
        status=state.status,
        status_css=state.status,
        phase=state.phase,
        cost=state.cost_so_far,
        duration_fmt=_fmt_duration(duration_s),
        started_at_fmt=started_dt.strftime("%Y-%m-%d %H:%M UTC"),
        generated_at=datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        executive_summary_html=executive_summary_html,
        phase_costs=phase_costs,
        cost_chart_svg=cost_chart_svg,
        duration_chart_svg=duration_chart_svg,
        deliverables=_deliverable_list(workspace_path),
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
