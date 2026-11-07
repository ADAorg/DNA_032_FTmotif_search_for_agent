#!/usr/bin/env python3
"""Edit a rendered site map SVG for presentation only; never touch a site's position.

Why this exists: `sitemap()` in the notebook hardcodes colours and size, so the
`figure:` section of `my_settings.yaml` / `run_config.yaml` had no effect on
anything asked for mid-conversation ("make it bold", "drop this gene from the
picture", "use our palette"). Re-running the notebook for every such request
also meant touching and re-executing analysis code for a purely visual change,
which is exactly what the skill's analysis-versus-presentation rule exists to
avoid.

Since 2026-11-07 `sitemap()` renders with `svg.fonttype: none` (so labels and
the TSS/x-axis/legend text are real, selectable <text> elements, not glyph
outlines) and tags every lane, gene label, motif's sites, the TSS line/label,
the title, the x-axis label and the legend with a stable `gid` (SVG `id`).
This script edits only those tagged elements, and only their presentation
attributes:

    - fill / stroke colour            (--recolor)
    - visibility of a whole gene lane (--hide-gene)
    - text content                    (--set-text)
    - font-weight / font-size         (--bold, --font-size)
    - marker shape                    (--marker-shape)

It never writes a coordinate, a `transform`, or anything inside a path's `d`
except the one case (--marker-shape) where the new shape is generated FROM the
marker's own existing bounding box, so a point that was bigger because it was
more significant stays exactly as big — the shape changes, the size doesn't.
The self-check at the end of _swap_marker_shape() enforces that in code, not
just in a docstring.

The genes, sites and their positions never pass through this script at all:
it reads and writes only the SVG. Nothing it does can need "comparable with a
different window / threshold" caveats, because nothing analytical is touched.

After editing, PNG and PDF are regenerated FROM THE EDITED SVG (via cairosvg,
`pip install cairosvg`) so all three formats in the zip show the same figure;
skip this with --no-reexport if cairosvg is unavailable, and say so to the
user rather than shipping an SVG that disagrees with its own PNG/PDF.

With --log, each call also appends what it did to a requested_changes.md
register (created if missing) -- the "Applied" entries are written by this
script from what it actually changed, not recalled by the agent afterwards,
so they can't silently drift from what happened. Call it again for a later
edit in the same run and it appends in order rather than overwriting.

Usage (repeatable flags may be given more than once):
    python restyle_sitemap.py SITEMAP.svg \\
        --recolor Spic=#1B9E77 --recolor Bach1=#D95F02 \\
        --hide-gene Sqstm1 \\
        --set-text title="Nrf2 network, Hmox1 panel" --bold title \\
        --marker-shape Spic=circle \\
        --log requested_changes.md \\
        [--no-reexport]

Exit 0 and a one-line summary of every change on success; exit 1 and nothing
written if a requested gene, motif or gid cannot be found (so a typo is
reported, not silently ignored).
"""
from __future__ import annotations

import argparse
import copy
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

SVG_NS = "http://www.w3.org/2000/svg"
XLINK_NS = "http://www.w3.org/1999/xlink"
ET.register_namespace("", SVG_NS)
ET.register_namespace("xlink", XLINK_NS)


def _tag(name: str) -> str:
    return f"{{{SVG_NS}}}{name}"


NUM = r"-?\d+\.?\d*(?:[eE][+-]?\d+)?"
HEX6 = re.compile(r"(?<![0-9a-fA-F])#([0-9a-fA-F]{6})(?![0-9a-fA-F])")
FILL_STYLE = re.compile(r"(fill:\s*)#([0-9a-fA-F]{6})\b", re.IGNORECASE)


def _href(use_elem: ET.Element) -> str | None:
    h = use_elem.get(f"{{{XLINK_NS}}}href") or use_elem.get("href")
    return h.lstrip("#") if h else None


def _set_href(use_elem: ET.Element, new_target_id: str) -> None:
    key = f"{{{XLINK_NS}}}href" if f"{{{XLINK_NS}}}href" in use_elem.attrib else "href"
    use_elem.set(key, f"#{new_target_id}")


def _iter_marker_instances(group: ET.Element, by_id: dict[str, ET.Element]):
    """Yield (position_elem, shape_elem) for each drawn marker in `group`.

    Matplotlib draws a collection's markers two different ways depending on
    whether every point in it happens to share one size: inline, as one
    <path> per point (common — sizes vary with -log10(p-value)); or as one
    shared <defs><path> plus one <use> per point (the fast path, which also
    triggers trivially whenever a (motif, strand) group has only one site).
    Both must be handled, or a motif with few sites silently breaks.

    position_elem is what carries the on-page position (the <path> itself,
    or the <use>); shape_elem is what carries the outline to resize/reshape
    (the same <path>, or the <defs> one the <use> points at).
    """
    def walk(elem):
        for child in elem:
            if child.tag == _tag("defs"):
                continue  # a template, referenced via <use>; never a marker on its own
            if child.tag == _tag("path"):
                yield child, child
            elif child.tag == _tag("use"):
                target = by_id.get(_href(child) or "")
                if target is not None and target.tag == _tag("path"):
                    yield child, target
            else:
                yield from walk(child)

    yield from walk(group)


def _marker_y(position_elem: ET.Element) -> float | None:
    if position_elem.tag == _tag("use"):
        y = position_elem.get("y")
        return float(y) if y is not None else None
    try:
        return _bbox_center(_path_bbox(position_elem.get("d", "")))[1]
    except RestyleError:
        return None


class RestyleError(Exception):
    """A requested edit could not be applied; nothing is written."""


def _load(svg_path: Path) -> tuple[ET.ElementTree, ET.Element, dict[str, ET.Element], dict[ET.Element, ET.Element]]:
    tree = ET.parse(svg_path)
    root = tree.getroot()
    by_id: dict[str, ET.Element] = {}
    parent_of: dict[ET.Element, ET.Element] = {}
    for parent in root.iter():
        for child in parent:
            parent_of[child] = parent
            gid = child.get("id")
            if gid:
                by_id.setdefault(gid, child)
    return tree, root, by_id, parent_of


def _text_of(elem: ET.Element) -> str:
    return "".join(elem.itertext()).strip()


def _numbers(d: str) -> list[float]:
    return [float(n) for n in re.findall(NUM, d)]


def _path_bbox(d: str) -> tuple[float, float, float, float]:
    nums = _numbers(d)
    if len(nums) < 4 or len(nums) % 2:
        raise RestyleError(f"path 'd' does not look like a simple polygon: {d!r}")
    xs, ys = nums[0::2], nums[1::2]
    return min(xs), min(ys), max(xs), max(ys)


def _bbox_center(bbox: tuple[float, float, float, float]) -> tuple[float, float]:
    x0, y0, x1, y1 = bbox
    return (x0 + x1) / 2, (y0 + y1) / 2


SHAPES = ("circle", "square", "diamond", "triangle-up", "triangle-down")


def _shape_path(shape: str, bbox: tuple[float, float, float, float]) -> str:
    """An SVG path 'd' for `shape`, filling exactly `bbox` -- same size, new outline."""
    x0, y0, x1, y1 = bbox
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    rx, ry = (x1 - x0) / 2, (y1 - y0) / 2
    if shape == "circle":
        k = 0.5522847498  # cubic-Bezier circle approximation constant
        return (f"M {cx - rx},{cy} "
                f"C {cx - rx},{cy - k * ry} {cx - k * rx},{cy - ry} {cx},{cy - ry} "
                f"C {cx + k * rx},{cy - ry} {cx + rx},{cy - k * ry} {cx + rx},{cy} "
                f"C {cx + rx},{cy + k * ry} {cx + k * rx},{cy + ry} {cx},{cy + ry} "
                f"C {cx - k * rx},{cy + ry} {cx - rx},{cy + k * ry} {cx - rx},{cy} Z")
    if shape == "square":
        return f"M {x0},{y0} L {x1},{y0} L {x1},{y1} L {x0},{y1} Z"
    if shape == "diamond":
        return f"M {cx},{y0} L {x1},{cy} L {cx},{y1} L {x0},{cy} Z"
    if shape == "triangle-up":
        return f"M {cx},{y0} L {x1},{y1} L {x0},{y1} Z"
    if shape == "triangle-down":
        return f"M {x0},{y0} L {x1},{y0} L {cx},{y1} Z"
    raise RestyleError(f"unknown shape {shape!r}; choose from {', '.join(SHAPES)}")


# --------------------------------------------------------------------------
# Operations. Each one touches only the attributes named in the module
# docstring, and raises RestyleError (not a silent no-op) if its target
# cannot be found.
# --------------------------------------------------------------------------

def recolor(root: ET.Element, by_id: dict[str, ET.Element], motif: str, new_hex: str) -> str:
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", new_hex):
        raise RestyleError(f"--recolor colour must be '#rrggbb'; got {new_hex!r}")
    group_ids = [gid for gid in by_id if gid.startswith(f"sites_{motif}_")]
    if not group_ids:
        known = sorted({gid.split("_", 2)[1] for gid in by_id if gid.startswith("sites_")})
        raise RestyleError(f"no motif {motif!r} in this figure; present: {', '.join(known) or '(none)'}")

    # Only ever match a FILL colour, never a stroke: every marker's border is
    # a fixed white/black outline unrelated to which motif it is, and a few
    # motifs share that same white stroke in their <defs> shape definition
    # (see _iter_marker_instances), so matching any hex would pick that up.
    old_hex = None
    for gid in group_ids:
        for position_elem, shape_elem in _iter_marker_instances(by_id[gid], by_id):
            for elem in (position_elem, shape_elem):
                m = FILL_STYLE.search(elem.get("style", ""))
                if m:
                    old_hex = f"#{m.group(2)}"
                    break
            if old_hex:
                break
        if old_hex:
            break
    if old_hex is None:
        raise RestyleError(f"could not find {motif}'s current fill colour to replace")

    count = 0
    for elem in root.iter():
        style = elem.get("style")
        if style:
            new_style, n = FILL_STYLE.subn(
                lambda m: m.group(1) + new_hex if m.group(2).lower() == old_hex[1:].lower() else m.group(0),
                style)
            if n and new_style != style:
                elem.set("style", new_style)
                count += 1
        fill_attr = elem.get("fill")
        if fill_attr and fill_attr.lower() == old_hex.lower():
            elem.set("fill", new_hex)
            count += 1
    if count == 0:
        raise RestyleError(f"found {motif}'s colour {old_hex} once but could not locate it to replace")
    return f"recoloured {motif}: {old_hex} -> {new_hex} ({count} element(s), including the legend swatch if present)"


def _lane_y(path_elem: ET.Element) -> float:
    d = path_elem.get("d", "")
    nums = _numbers(d)
    if len(nums) < 4:
        raise RestyleError(f"lane path does not look like a line: {d!r}")
    return nums[1]  # constant for a horizontal line: y of the first point


def hide_gene(root: ET.Element, by_id: dict[str, ET.Element],
               parent_of: dict[ET.Element, ET.Element], gene: str) -> str:
    label_id = None
    for gid, elem in by_id.items():
        if gid.startswith("label_") and _text_of(elem).lower() == gene.lower():
            label_id = gid
            break
    if label_id is None:
        known = sorted(_text_of(e) for g, e in by_id.items() if g.startswith("label_"))
        raise RestyleError(f"no gene named {gene!r} in this figure; present: {', '.join(known) or '(none)'}")

    suffix = label_id[len("label_"):]
    lane_id = f"lane_{suffix}"
    lane = by_id.get(lane_id)
    if lane is None:
        raise RestyleError(f"found label {label_id!r} but no matching {lane_id!r}")
    lane_path = lane.find(_tag("path"))
    if lane_path is None:
        raise RestyleError(f"{lane_id!r} has no <path> to read its position from")
    target_y = _lane_y(lane_path)

    # Tolerance: a fraction of the spacing between lanes, so only markers on
    # THIS lane are caught even when two lanes sit close together.
    all_y = sorted({_lane_y(e.find(_tag("path"))) for g, e in by_id.items()
                     if g.startswith("lane_") and e.find(_tag("path")) is not None})
    spacing = min((b - a for a, b in zip(all_y, all_y[1:])), default=None)
    tol = 0.4 * spacing if spacing else 8.0

    removed_sites = 0
    for gid, group in list(by_id.items()):
        if not gid.startswith("sites_"):
            continue
        for position_elem, _shape_elem in list(_iter_marker_instances(group, by_id)):
            y = _marker_y(position_elem)
            if y is not None and abs(y - target_y) <= tol:
                parent_of[position_elem].remove(position_elem)
                removed_sites += 1

    parent_of[lane].remove(lane)
    parent_of[by_id[label_id]].remove(by_id[label_id])
    return (f"hid {gene}: removed its lane, its label and {removed_sites} site marker(s) "
            f"from the picture (the hits table and raw scan for {gene} are untouched)")


def _insert_title(root: ET.Element, by_id: dict[str, ET.Element], text: str) -> str:
    """Add a title where sitemap() leaves none -- even an empty one would have
    reserved its row and shifted the plot, so the baseline figure has none."""
    axes = next((e for e in root.iter(_tag("g")) if e.get("id") == "axes_1"), None)
    if axes is None:
        raise RestyleError("could not find the axes to attach a title to")
    xlabel = by_id.get("xlabel")
    xlabel_text = (xlabel.find(f".//{_tag('text')}") if xlabel is not None else None)
    if xlabel_text is None or xlabel_text.get("x") is None:
        raise RestyleError("could not centre a new title: no 'xlabel' text found")
    cx = xlabel_text.get("x")

    lane_ys = [_lane_y(e.find(_tag("path"))) for gid, e in by_id.items()
               if gid.startswith("lane_") and e.find(_tag("path")) is not None]
    top_y = min(lane_ys) if lane_ys else 20.0
    title_y = top_y - 25.0  # approximate; nudge with --font-size if it overlaps

    g = ET.SubElement(axes, _tag("g"))
    g.set("id", "title")
    t = ET.SubElement(g, _tag("text"))
    t.set("style", "font: 12px 'DejaVu Sans', sans-serif; text-anchor: middle")
    t.set("x", cx)
    t.set("y", f"{title_y}")
    t.text = text
    by_id["title"] = g
    return f"added a title: {text!r} (position is approximate -- check the re-exported image)"


def set_text(root: ET.Element, by_id: dict[str, ET.Element], gid: str, new_text: str) -> str:
    elem = by_id.get(gid)
    if elem is None:
        if gid == "title":
            return _insert_title(root, by_id, new_text)
        raise RestyleError(f"no element with gid {gid!r} in this figure")
    text_elem = elem if elem.tag == _tag("text") else elem.find(f".//{_tag('text')}")
    if text_elem is None:
        raise RestyleError(
            f"{gid!r} has no <text> to edit -- was this SVG rendered with "
            "svg.fonttype: none? Older runs rendered text as glyph outlines."
        )
    for child in list(text_elem):
        text_elem.remove(child)
    text_elem.text = new_text
    return f"set text of {gid!r} to {new_text!r}"


def _text_style(by_id: dict[str, ET.Element], gid: str) -> ET.Element:
    elem = by_id.get(gid)
    if elem is None:
        raise RestyleError(f"no element with gid {gid!r} in this figure")
    text_elem = elem if elem.tag == _tag("text") else elem.find(f".//{_tag('text')}")
    if text_elem is None:
        raise RestyleError(
            f"{gid!r} has no <text> to restyle -- was this SVG rendered with "
            "svg.fonttype: none? Older runs rendered text as glyph outlines."
        )
    return text_elem


def set_font_weight(by_id: dict[str, ET.Element], gid: str, weight: str) -> str:
    text_elem = _text_style(by_id, gid)
    style = text_elem.get("style", "")
    style = re.sub(r"font-weight:\s*[^;]+;?\s*", "", style).rstrip("; ")
    style = f"{style}; font-weight: {weight}" if style else f"font-weight: {weight}"
    text_elem.set("style", style)
    return f"set font-weight of {gid!r} to {weight!r}"


def set_font_size(by_id: dict[str, ET.Element], gid: str, size_px: float) -> str:
    text_elem = _text_style(by_id, gid)
    style = text_elem.get("style", "")
    new_style = re.sub(r"font:\s*[\d.]+px", f"font: {size_px:g}px", style)
    if new_style == style:
        raise RestyleError(f"{gid!r}'s style has no 'font: Npx ...' to resize: {style!r}")
    text_elem.set("style", new_style)
    return f"set font size of {gid!r} to {size_px:g}px"


def _use_refcount(root: ET.Element) -> dict[str, int]:
    counts: dict[str, int] = {}
    for elem in root.iter(_tag("use")):
        href = _href(elem)
        if href:
            counts[href] = counts.get(href, 0) + 1
    return counts


def swap_marker_shape(root: ET.Element, by_id: dict[str, ET.Element],
                      parent_of: dict[ET.Element, ET.Element], motif: str, shape: str) -> str:
    if shape not in SHAPES:
        raise RestyleError(f"--marker-shape must be one of {', '.join(SHAPES)}; got {shape!r}")
    group_ids = [gid for gid in by_id if gid.startswith(f"sites_{motif}_")]
    if not group_ids:
        known = sorted({gid.split("_", 2)[1] for gid in by_id if gid.startswith("sites_")})
        raise RestyleError(f"no motif {motif!r} in this figure; present: {', '.join(known) or '(none)'}")

    refcount = _use_refcount(root)
    edited_defs: set[str] = set()
    clone_n = 0
    count = 0
    for gid in group_ids:
        for position_elem, shape_elem in _iter_marker_instances(by_id[gid], by_id):
            old_d = shape_elem.get("d", "")
            bbox = _path_bbox(old_d)
            new_d = _shape_path(shape, bbox)
            # Self-check: the invariant this whole script exists to protect.
            if _bbox_center(_path_bbox(new_d)) != _bbox_center(bbox):
                raise RestyleError("internal error: new marker shape moved the point; aborting, nothing written")

            if shape_elem is position_elem:
                # An inline <path>: nothing else can reference it, safe to edit directly.
                shape_elem.set("d", new_d)
                count += 1
                continue

            def_id = shape_elem.get("id", "")
            if def_id in edited_defs:
                count += 1  # a sibling <use> of an already-resized shared shape
                continue
            if refcount.get(def_id, 0) > 1:
                # Shared with a <use> this call isn't touching (e.g. another
                # motif that happens to need the same marker size) -- clone
                # the shape instead of reshaping everyone who points at it.
                clone_n += 1
                clone = copy.deepcopy(shape_elem)
                clone.set("id", f"restyle_shape_{motif}_{clone_n}")
                clone.set("d", new_d)
                parent_of[shape_elem].append(clone)
                _set_href(position_elem, clone.get("id"))
                refcount[def_id] -= 1
            else:
                shape_elem.set("d", new_d)
                edited_defs.add(def_id)
            count += 1
    return f"changed {motif}'s marker shape to {shape} ({count} marker(s), each resized to fit its own original size)"


def _append_log(log_path: Path, svg_name: str, messages: list[str]) -> str:
    """Append this run's applied changes to a requested_changes.md register.

    Written by the script itself, from the same `messages` it prints to the
    terminal, so the "Applied" section is a record of what actually ran, not
    of what someone remembers running. Everything the script cannot know
    about -- a refused request, one applied by editing the notebook copy
    instead -- is added by hand, in the same file, under the sections this
    function leaves for that.
    """
    run_name = log_path.resolve().parent.name
    if not log_path.is_file():
        log_path.write_text(
            f"# Requested changes — {run_name}\n\n"
            "Entries under \"Applied\" are written by restyle_sitemap.py itself, from "
            "the changes it just made: the script only ever writes colour, text and "
            "shape attributes, and checks before writing that no marker moved, so an "
            "entry here cannot describe a change to where a site lies. Anything else "
            "the user asked for -- refused, not possible here, or needing the "
            "maintainer -- is added below by hand, in the user's own words.\n\n"
            "## Applied\n\n"
            "## Refused or not possible\n\n"
            "## For the maintainer\n"
        )
    text = log_path.read_text()
    marker = "## Applied\n"
    # The file may already exist without this heading -- created by hand, by
    # an earlier version of this script, or mid-edit by the agent -- so don't
    # assume it's there just because the file is. Add any missing section
    # heading rather than failing on it.
    for heading in ("## Applied\n", "## Refused or not possible\n", "## For the maintainer\n"):
        if heading not in text:
            if not text.endswith("\n"):
                text += "\n"
            text += ("\n" if text.strip() else "") + heading
    timestamp = datetime.now().isoformat(timespec="seconds")
    entries = "".join(f"- [{timestamp}] {svg_name}: {m}\n" for m in messages)
    # Append at the END of the "## Applied" section (right before the next
    # "## " heading, or at the end of the file if "## Applied" is the last
    # section), so repeated calls accumulate in chronological order instead
    # of each new entry pushing the previous ones down.
    start = text.index(marker) + len(marker)
    next_heading_pos = text.find("\n## ", start)
    end = next_heading_pos if next_heading_pos != -1 else len(text)
    section = text[start:end].strip("\n")
    new_section = (section + "\n" + entries) if section else entries
    log_path.write_text(text[:start] + "\n" + new_section + text[end:])
    return f"recorded this run's changes in {log_path}"


def reexport(svg_path: Path) -> list[str]:
    try:
        import cairosvg
    except ImportError:
        return ["WARN  cairosvg not installed; PNG and PDF were NOT regenerated and now "
                "disagree with the edited SVG -- `pip install cairosvg` and re-run, or "
                "pass --no-reexport and tell the user only the SVG was updated"]
    msgs = []
    png_path = svg_path.with_suffix(".png")
    pdf_path = svg_path.with_suffix(".pdf")
    cairosvg.svg2png(url=str(svg_path), write_to=str(png_path), dpi=200)
    msgs.append(f"re-exported {png_path.name} from the edited SVG")
    cairosvg.svg2pdf(url=str(svg_path), write_to=str(pdf_path))
    msgs.append(f"re-exported {pdf_path.name} from the edited SVG")
    return msgs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("svg", type=Path, help="the sitemap_*.svg to edit, in place")
    ap.add_argument("--recolor", action="append", default=[], metavar="MOTIF=#RRGGBB")
    ap.add_argument("--hide-gene", action="append", default=[], metavar="GENE")
    ap.add_argument("--set-text", action="append", default=[], metavar="GID=TEXT",
                    help="GID is one of: title, xlabel, tss_label, legend")
    ap.add_argument("--bold", action="append", default=[], metavar="GID")
    ap.add_argument("--font-size", action="append", default=[], metavar="GID=PX")
    ap.add_argument("--marker-shape", action="append", default=[], metavar="MOTIF=SHAPE",
                    help=f"SHAPE is one of: {', '.join(SHAPES)}")
    ap.add_argument("--no-reexport", action="store_true",
                    help="skip regenerating PNG/PDF from the edited SVG")
    ap.add_argument("--log", metavar="PATH",
                    help="append this run's applied changes to a requested_changes.md "
                         "register at PATH (created if missing)")
    args = ap.parse_args()

    if not args.svg.is_file():
        print(f"FAIL  not a file: {args.svg}", file=sys.stderr)
        return 1

    tree, root, by_id, parent_of = _load(args.svg)
    original = copy.deepcopy(root)
    messages: list[str] = []

    try:
        for spec in args.recolor:
            motif, _, hexval = spec.partition("=")
            messages.append(recolor(root, by_id, motif, hexval))
        for gene in args.hide_gene:
            messages.append(hide_gene(root, by_id, parent_of, gene))
        for spec in args.set_text:
            gid, _, text = spec.partition("=")
            messages.append(set_text(root, by_id, gid, text))
        for gid in args.bold:
            messages.append(set_font_weight(by_id, gid, "bold"))
        for spec in args.font_size:
            gid, _, px = spec.partition("=")
            messages.append(set_font_size(by_id, gid, float(px)))
        for spec in args.marker_shape:
            motif, _, shape = spec.partition("=")
            messages.append(swap_marker_shape(root, by_id, parent_of, motif, shape))
    except RestyleError as e:
        print(f"FAIL  {e}", file=sys.stderr)
        print("      nothing was written.", file=sys.stderr)
        return 1

    if not messages:
        print("FAIL  no edit requested (pass at least one of --recolor, --hide-gene, "
              "--set-text, --bold, --font-size, --marker-shape)", file=sys.stderr)
        return 1

    # Geometry self-check: every element present in both versions, other than
    # ones we deliberately removed or whose `d` we deliberately rewrote above,
    # must have an identical `d`/position. This is what makes "never touches
    # a site's position" a checked fact rather than a claim.
    def _inside_sites_group(elem: ET.Element) -> bool:
        p = parent_of.get(elem)
        while p is not None:
            pid = p.get("id")
            if pid and pid.startswith("sites_"):
                return True
            p = parent_of.get(p)
        return False

    before_by_id = {e.get("id"): e for e in original.iter() if e.get("id")}
    for gid, before in before_by_id.items():
        after = by_id.get(gid)
        if after is None or gid.startswith("lane_") or gid.startswith("sites_") or _inside_sites_group(after):
            continue
        if before.get("d") and before.get("d") != after.get("d"):
            print(f"FAIL  internal error: {gid!r}'s geometry changed unexpectedly; nothing written", file=sys.stderr)
            return 1

    tree.write(args.svg, encoding="unicode", xml_declaration=False)
    # ElementTree drops the XML prolog; put back what a browser/renderer expects.
    args.svg.write_text('<?xml version="1.0" encoding="UTF-8"?>\n' + args.svg.read_text())

    print(f"OK    {args.svg}", file=sys.stderr)
    for m in messages:
        print(f"      {m}", file=sys.stderr)
    if not args.no_reexport:
        for m in reexport(args.svg):
            print(f"      {m}", file=sys.stderr)
    if args.log:
        print(f"      {_append_log(Path(args.log), args.svg.name, messages)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
