"""Check that every link and form target in the templates matches a real route.

    python scripts/check_links.py

A dead ``href`` only shows up as a 404 when somebody clicks it, which during a
five-minute demo means it shows up in front of the marker.  This reads the route
decorators out of ``app/routers/*.py``, reads every ``href=`` and ``action=`` out
of the templates, and reports any target that no route can serve.

Both sides are matched as patterns, not strings: a route declared
``/property/{property_id}`` is stored as ``/property/*``, and a template link
built as ``/property/{{ p.property_id }}/inquire`` collapses to
``/property/*/inquire``, so they compare equal.  Query strings and ``#anchors``
are dropped, and anything Jinja-generated that cannot be reduced to a literal
path (``{{ url }}``) is reported as skipped rather than guessed at.
"""
from __future__ import annotations

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ROUTER_DIR = PROJECT_ROOT / "app" / "routers"
TEMPLATE_DIR = PROJECT_ROOT / "app" / "templates"

_PREFIX = re.compile(r"""APIRouter\(\s*prefix\s*=\s*["']([^"']*)["']""")
# The path may be an empty string: a prefixed router's landing page is declared
# @router.get(""), which serves /admin, /agent or /me exactly.
_ROUTE = re.compile(r"""@router\.(get|post)\(\s*["']([^"']*)["']""")
# DOTALL, because an action= can be a Jinja conditional wrapped over two lines.
_TARGET = re.compile(r"""(?:href|action)\s*=\s*"([^"]*)\"""", re.DOTALL)
_BRACED = re.compile(r"\{[^{}]*\}")          # /property/{property_id}
_JINJA = re.compile(r"\{\{.*?\}\}", re.DOTALL)   # /property/{{ p.id }}
# Path literals inside a Jinja expression: {{ '/agent/x' if p else '/agent/y' }}
_LITERAL = re.compile(r"'(/[^']*)'")
# Jinja's ~ concatenation, so '/agent/properties/' ~ p.id ~ '/edit' is read as
# one path rather than as two unrelated literals.  Collapse the interpolated
# term to * -- first when it sits between two literals, then when it trails one.
_CONCAT_MID = re.compile(r"'\s*~\s*[^'~}]+~\s*'")
_CONCAT_END = re.compile(r"'\s*~\s*[^'~}]+")


def routes() -> set[str]:
    """Every path the application serves, reduced to a comparable pattern."""
    found: set[str] = set()
    for path in sorted(ROUTER_DIR.glob("*.py")):
        source = path.read_text(encoding="utf-8")
        prefix_match = _PREFIX.search(source)
        prefix = prefix_match.group(1) if prefix_match else ""
        for _method, route in _ROUTE.findall(source):
            found.add(_BRACED.sub("*", prefix + route).rstrip("/") or "/")
    return found


def targets() -> dict[str, list[str]]:
    """Every internal link target, mapped to the templates that use it."""
    used: dict[str, list[str]] = {}
    for path in sorted(TEMPLATE_DIR.rglob("*.html")):
        name = path.relative_to(TEMPLATE_DIR).as_posix()
        for raw in _TARGET.findall(path.read_text(encoding="utf-8")):
            used.setdefault(raw, []).append(name)
    return used


def _normalise(target: str) -> str:
    """Reduce one literal path to a comparable pattern."""
    target = target.split("?")[0].split("#")[0]
    return _JINJA.sub("*", target).rstrip("/") or "/"


def classify(raw: str) -> tuple[str, list[str]]:
    """Return (verdict, patterns-to-check) for one raw href/action value."""
    value = raw.strip()

    if not value or value.startswith(("#", "mailto:", "tel:", "http://",
                                      "https://", "//", "javascript:")):
        return "external", []

    # The whole value is a Jinja expression.  If it picks between literal paths
    # -- action="{{ '/a/edit' if p else '/a/new' }}" -- check every branch.
    if value.startswith("{{"):
        joined = _CONCAT_END.sub("*'", _CONCAT_MID.sub("*", value))
        literals = [_normalise(lit) for lit in _LITERAL.findall(joined)]
        return ("check", literals) if literals else ("dynamic", [])

    if value.startswith("/static/"):
        return "static", []
    if not value.startswith("/"):
        return "relative", []           # nothing in this project uses these
    if "{%" in value:
        return "dynamic", []            # built by an if/for -- cannot reduce

    return "check", [_normalise(value)]


def main() -> int:
    known = routes()
    print(f"  {len(known)} route(s) found in app/routers/\n")

    dead: list[tuple[str, str, list[str]]] = []
    skipped: list[tuple[str, list[str]]] = []
    checked = 0

    for raw, templates in sorted(targets().items()):
        verdict, patterns = classify(raw)
        if verdict == "check":
            for pattern in patterns:
                checked += 1
                if pattern not in known and pattern + "/" not in known:
                    dead.append((raw, pattern, templates))
        elif verdict in ("dynamic", "relative"):
            skipped.append((raw, templates))

    for raw, pattern, templates in dead:
        print(f"  DEAD  {' '.join(raw.split())}")
        print(f"        no route matches {pattern}")
        print(f"        used in: {', '.join(sorted(set(templates)))}")

    if skipped:
        print("  Not checked (assembled at render time):")
        for raw, templates in skipped:
            print(f"    {' '.join(raw.split())}"
                  f"   [{', '.join(sorted(set(templates)))}]")

    print(f"\n  {checked} internal link(s) checked, {len(dead)} dead")
    return 1 if dead else 0


if __name__ == "__main__":
    raise SystemExit(main())
