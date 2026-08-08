"""Generate apps/holodeck/data/worktree-colors.png from worktree-colors.yaml."""

from datetime import datetime
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    Image = None
    ImageDraw = None
    ImageFont = None

WORKTREE_COLORS_REL = Path("apps/holodeck/worktree-colors.yaml")
PALETTE_PNG_REL = Path("apps/holodeck/data/worktree-colors.png")
COLS = 4
CELL_W = 320
CELL_H = 200
PAD = 16
SWATCH_H = 72
TITLE_H = 64

### Paths
def repo_root_from_here():
    return Path(__file__).resolve().parents[2]
def colors_yaml_path(repo_root=None):
    root = Path(repo_root) if repo_root else repo_root_from_here()
    return root / WORKTREE_COLORS_REL
def palette_png_path(repo_root=None):
    root = Path(repo_root) if repo_root else repo_root_from_here()
    return root / PALETTE_PNG_REL

### Load / format
def load_colors_doc(repo_root=None):
    if yaml is None:
        return None
    path = colors_yaml_path(repo_root)
    if not path.is_file():
        return None
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return None
def rule_match_lines(rule):
    lines = []
    if rule.get("name_exact"):
        lines.append("name_exact: " + str(rule["name_exact"]))
    if rule.get("branch"):
        lines.append("branch: " + str(rule["branch"]))
    if rule.get("name_contains"):
        lines.append("name_contains: " + str(rule["name_contains"]))
    contains_all = rule.get("name_contains_all")
    if contains_all:
        if isinstance(contains_all, (list, tuple)):
            joined = ", ".join(str(part) for part in contains_all)
            lines.append("name_contains_all: [" + joined + "]")
        else:
            lines.append("name_contains_all: " + str(contains_all))
    return lines or ["(no match fields)"]
def parse_hex_rgb(value):
    text = str(value or "").strip().lstrip("#")
    if len(text) != 6:
        return 0, 0, 0
    try:
        return int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16)
    except ValueError:
        return 0, 0, 0
def swatch_foreground(background, preferred=None):
    """Readable text color on the swatch (dark on light colors, white otherwise)."""
    _ = preferred
    br, bg, bb = parse_hex_rgb(background)
    lum = (0.2126 * br + 0.7152 * bg + 0.0722 * bb) / 255
    return "#111111" if lum >= 0.55 else "#ffffff"
def load_fonts():
    font_paths = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    font_bold = ImageFont.load_default()
    font_reg = ImageFont.load_default()
    font_title = ImageFont.load_default()
    font_swatch = ImageFont.load_default()
    for path in font_paths:
        if not Path(path).is_file():
            continue
        try:
            regular = path.replace(" Bold", "") if " Bold" in path else path
            font_bold = ImageFont.truetype(path if "Bold" in path else regular, 18)
            font_reg = ImageFont.truetype(regular, 14)
            font_title = ImageFont.truetype(path if "Bold" in path else regular, 22)
            font_swatch = ImageFont.truetype(path if "Bold" in path else regular, 16)
            break
        except OSError:
            continue
    return font_title, font_bold, font_reg, font_swatch

### Render
def render_palette_image(colors_doc, created_at=None):
    if Image is None:
        raise RuntimeError("Pillow is required to render worktree-colors.png")
    foreground = colors_doc.get("foreground") or "#ffffff"
    rules = [rule for rule in (colors_doc.get("rules") or []) if isinstance(rule, dict) and rule.get("background")]
    cols = COLS
    rows = max(1, (len(rules) + cols - 1) // cols)
    img_w = cols * CELL_W + PAD
    img_h = TITLE_H + rows * CELL_H + PAD
    img = Image.new("RGB", (img_w, img_h), "#1a1a1a")
    draw = ImageDraw.Draw(img)
    font_title, font_bold, font_reg, font_swatch = load_fonts()
    stamp = created_at or datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    draw.text((PAD, 8), "worktree-colors palette", fill="#ffffff", font=font_title)
    draw.text((PAD, 36), "created: " + stamp, fill="#9a9a9a", font=font_reg)
    for index, rule in enumerate(rules):
        col = index % cols
        row = index // cols
        x0 = PAD // 2 + col * CELL_W
        y0 = TITLE_H + row * CELL_H
        x1 = x0 + CELL_W - 12
        y1 = y0 + CELL_H - 12
        background = str(rule.get("background") or "#245f99")
        text_fg = swatch_foreground(background, rule.get("foreground") or foreground)
        rule_id = str(rule.get("id") or "(unnamed)")
        draw.rounded_rectangle([x0, y0, x1, y1], radius=10, fill="#2a2a2a")
        draw.rounded_rectangle([x0 + 10, y0 + 10, x1 - 10, y0 + 10 + SWATCH_H], radius=8, fill=background)
        draw.text((x0 + 18, y0 + 34), rule_id, fill=text_fg, font=font_swatch)
        ty = y0 + 10 + SWATCH_H + 12
        draw.text((x0 + 14, ty), background, fill="#d0d0d0", font=font_reg)
        ty += 22
        for line in rule_match_lines(rule):
            draw.text((x0 + 14, ty), line, fill="#d0d0d0", font=font_reg)
            ty += 18
    return img
def write_worktree_colors_palette(repo_root=None, output_path=None):
    """Render the palette PNG. Returns the output path, or None if skipped."""
    if Image is None:
        print("worktree-colors palette: skipped (Pillow not installed)")
        return None
    if yaml is None:
        print("worktree-colors palette: skipped (PyYAML not installed)")
        return None
    colors_doc = load_colors_doc(repo_root)
    if not colors_doc:
        print("worktree-colors palette: skipped (worktree-colors.yaml missing or unreadable)")
        return None
    out = Path(output_path) if output_path else palette_png_path(repo_root)
    out.parent.mkdir(parents=True, exist_ok=True)
    created_at = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    img = render_palette_image(colors_doc, created_at=created_at)
    img.save(out, "PNG")
    print("worktree-colors palette: wrote " + str(out))
    return out

### CLI
def main(argv=None):
    write_worktree_colors_palette()
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
