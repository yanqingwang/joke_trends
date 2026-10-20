"""Tiny inline-SVG chart helpers. No external deps — output raw SVG strings."""


def sparkline(values: list, width: int = 240, height: int = 44, color: str = "#22a06b") -> str:
    vals = [float(v) for v in values if v is not None]
    if len(vals) < 2:
        return ""
    lo, hi = min(vals), max(vals)
    rng = (hi - lo) or 1.0
    step = width / (len(vals) - 1)
    pts = [f"{i*step:.1f},{height - 4 - (v - lo) / rng * (height - 10):.1f}" for i, v in enumerate(vals)]
    poly = " ".join(pts)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" role="img">'
            f'<polyline points="{poly}" fill="none" stroke="{color}" stroke-width="2"/></svg>')


def bar(values: list, labels: list, width: int = 640, height: int = 44, color: str = "#3b82f6") -> str:
    """Horizontal mini bar; labels below not supported in svg-free markdown so keep minimal."""
    if not values:
        return ""
    vals = [max(float(v), 0.0) for v in values]
    hi = max(vals) or 1.0
    bw = width / len(vals)
    bars = []
    for i, v in enumerate(vals):
        h = v / hi * (height - 8)
        bars.append(f'<rect x="{i*bw+2:.1f}" y="{height-4-h:.1f}" width="{bw-4:.1f}" height="{h:.1f}" fill="{color}"/>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" role="img">'
            + "".join(bars) + "</svg>")
