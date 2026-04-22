"""
Lucide icon SVGs — 18×18, stroke-width 1.5, currentColor.
All paths sourced from lucide.dev.
"""

def _svg(paths: str, size: int = 18) -> str:
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        f'stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">'
        f'{paths}</svg>'
    )


ICON_HOME = _svg(
    '<path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>'
    '<polyline points="9 22 9 12 15 12 15 22"/>'
)

ICON_SEARCH = _svg(
    '<circle cx="11" cy="11" r="8"/>'
    '<path d="m21 21-4.3-4.3"/>'
)

ICON_MAIL = _svg(
    '<rect width="20" height="16" x="2" y="4" rx="2"/>'
    '<path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/>'
)

ICON_CLIPBOARD = _svg(
    '<rect width="8" height="4" x="8" y="2" rx="1" ry="1"/>'
    '<path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/>'
    '<path d="M12 11h4"/><path d="M12 16h4"/>'
    '<path d="M8 11h.01"/><path d="M8 16h.01"/>'
)

ICON_CHART = _svg(
    '<path d="M3 3v18h18"/>'
    '<path d="M18 17V9"/>'
    '<path d="M13 17V5"/>'
    '<path d="M8 17v-3"/>'
)

ICON_CHECK = _svg('<path d="M20 6 9 17l-5-5"/>')

ICON_CHECK_CIRCLE = _svg(
    '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>'
    '<path d="m9 11 3 3L22 4"/>'
)

ICON_ARROW_RIGHT = _svg(
    '<path d="M5 12h14"/>'
    '<path d="m12 5 7 7-7 7"/>'
)

ICON_SPINNER = _svg('<path d="M21 12a9 9 0 1 1-6.219-8.56"/>')

ICON_SEND = _svg(
    '<path d="m22 2-7 20-4-9-9-4Z"/>'
    '<path d="M22 2 11 13"/>'
)

ICON_DOWNLOAD = _svg(
    '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>'
    '<polyline points="7 10 12 15 17 10"/>'
    '<line x1="12" x2="12" y1="15" y2="3"/>'
)

ICON_ALERT = _svg(
    '<circle cx="12" cy="12" r="10"/>'
    '<line x1="12" x2="12" y1="8" y2="12"/>'
    '<line x1="12" x2="12.01" y1="16" y2="16"/>'
)

ICON_SPARKLE = _svg(
    '<path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/>'
    '<path d="M5 3v4"/><path d="M19 17v4"/>'
    '<path d="M3 5h4"/><path d="M17 19h4"/>'
)

ICON_EXTERNAL = _svg(
    '<path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>'
    '<polyline points="15 3 21 3 21 9"/>'
    '<line x1="10" x2="21" y1="14" y2="3"/>'
)

ICON_REFRESH = _svg(
    '<path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/>'
    '<path d="M21 3v5h-5"/>'
    '<path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/>'
    '<path d="M8 16H3v5"/>'
)

ICON_X = _svg(
    '<path d="M18 6 6 18"/>'
    '<path d="m6 6 12 12"/>'
)

ICON_X_CIRCLE = _svg(
    '<circle cx="12" cy="12" r="10"/>'
    '<path d="m15 9-6 6"/>'
    '<path d="m9 9 6 6"/>'
)

ICON_CIRCLE = _svg('<circle cx="12" cy="12" r="10"/>')

ICON_TRENDING_UP = _svg(
    '<polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/>'
    '<polyline points="16 7 22 7 22 13"/>'
)

ICON_PACKAGE = _svg(
    '<path d="m7.5 4.27 9 5.15"/>'
    '<path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"/>'
    '<path d="m3.3 7 8.7 5 8.7-5"/>'
    '<path d="M12 22V12"/>'
)
