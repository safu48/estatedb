"""Compile every Jinja template and report failures.

    python scripts/check_templates.py

Templates are only parsed when a page is first requested, so a typo in a
rarely-visited page can sit unnoticed until the demo.  This parses all 32 at
once, which is quick and catches that whole class of mistake.

The custom filter names are read out of ``app/templating.py`` rather than listed
here, so adding a filter there does not turn this into a wall of false alarms.
They are registered as no-ops: the point is to parse the templates, not to run
them, and Jinja raises at parse time on a filter it has never heard of.
Importing the real module would pull in FastAPI and the database settings, which
this check has no business needing.
"""
from __future__ import annotations

import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = PROJECT_ROOT / "app" / "templates"
TEMPLATING_PY = PROJECT_ROOT / "app" / "templating.py"

_FILTER_LINE = re.compile(r"""filters\[\s*["']([A-Za-z_][A-Za-z0-9_]*)["']\s*\]""")


def registered_filters() -> list[str]:
    """Filter names assigned in app/templating.py, read from its source."""
    if not TEMPLATING_PY.exists():
        return []
    return sorted(set(_FILTER_LINE.findall(
        TEMPLATING_PY.read_text(encoding="utf-8"))))


def main() -> int:
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    names = registered_filters()
    for name in names:
        env.filters[name] = lambda value, *a, **k: value

    templates = sorted(p.relative_to(TEMPLATE_DIR).as_posix()
                       for p in TEMPLATE_DIR.rglob("*.html"))
    failed = 0

    print(f"  stubbed filters: {', '.join(names) or 'none found'}\n")
    for template in templates:
        try:
            env.get_template(template)
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"  FAIL  {template}\n        {type(exc).__name__}: {exc}")

    print(f"  {len(templates)} template(s) parsed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
