"""用 Pillow 把封面插画的几何渲染成 PNG，供本地核对构图与墨色浓淡。

为什么另开一条渲染路径：浏览器截图对密集线稿会超出工具体积上限（与页面高度无关），
所以直接用 Pillow 画同一份几何。几何数据与 SVG 完全共用
（make_cover_art 里的 CULMS / TWIGS / LEAVES / NODES / ROCK），只有渲染方式不同，
因此 PNG 与 SVG 的结果应当一致 —— 这个脚本只用来核对，不进产物。

用法：
    python tools/preview_cover_art.py [输出路径.png]
"""

import pathlib
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import make_cover_art as art  # noqa: E402

SS = 2  # 超采样倍数，缩小时做抗锯齿
SCALE = 0.58 * SS
PANEL = (int(art.W * SCALE), int(art.H * SCALE))

PAPER = (250, 246, 238)
INK = (26, 24, 21)
GRAPHITE = (110, 102, 89)
WASH = (42, 38, 32)
LABEL_FONT = r"C:\Windows\Fonts\msyh.ttc"


def sp(points):
    """几何坐标 → PNG 坐标。"""
    return [(x * SCALE, y * SCALE) for x, y in points]


def stroke(draw, points, color, width, alpha=255, closed=False):
    pts = sp(points)
    if closed and len(pts) > 1:
        pts = pts + [pts[0]]
    draw.line(pts, fill=color + (alpha,), width=max(1, int(round(width * SCALE))), joint="curve")


def fill(draw, points, color, alpha):
    draw.polygon(sp(points), fill=color + (alpha,))


def blank():
    return Image.new("RGBA", PANEL, PAPER + (255,))


def culm_outline(culm):
    return [(x, y) for x, y in culm["outline"] if y > -300]


def blur(layer, radius):
    return layer.filter(ImageFilter.GaussianBlur(max(0.5, radius * SCALE)))


def on_layer(draw_ops):
    layer = Image.new("RGBA", PANEL, (0, 0, 0, 0))
    draw_ops(ImageDraw.Draw(layer))
    return layer


# ------------------------------------------------------------------ 白描


def render_baimiao():
    """只有线：粗细一致，不皴不染。"""
    panel = blank()
    draw = ImageDraw.Draw(panel)

    for culm in art.CULMS:
        stroke(draw, culm_outline(culm), INK, 2.6, closed=True)
    for twig in art.TWIGS:
        stroke(draw, twig["spine"], INK, 2.0)
    for mark in art.NODES:
        stroke(draw, mark, INK, 2.5)
    for leaf in art.LEAVES:
        stroke(draw, leaf["outline"], INK, 2.0, closed=True)
        stroke(draw, leaf["spine"], INK, 1.1, alpha=128)  # 主脉
    stroke(draw, art.ROCK, INK, 2.4, closed=True)
    for rib in art.ROCK_RIBS:
        stroke(draw, rib, INK, 1.7)

    return panel


# ------------------------------------------------------------------ 素描


def render_sketch():
    """轮廓轻、排线密，明暗全由线条疏密表达。"""
    panel = blank()

    def ops(draw):
        for culm in art.CULMS:
            outline = culm_outline(culm)
            for offset, alpha in ((0, 190), (1.5, 98)):
                stroke(
                    draw,
                    [(x + offset, y + offset * 0.6) for x, y in outline],
                    GRAPHITE,
                    1.3,
                    alpha=alpha,
                    closed=True,
                )
            for run in art.hatch_lines(culm, spacing=5.4):
                stroke(draw, run, GRAPHITE, 1.05, alpha=132)

        for twig in art.TWIGS:
            stroke(draw, twig["spine"], GRAPHITE, 1.2, alpha=176)
        for mark in art.NODES:
            stroke(draw, mark, GRAPHITE, 1.6, alpha=168)

        for leaf in art.LEAVES:
            stroke(draw, leaf["outline"], GRAPHITE, 1.2, alpha=186, closed=True)
            for run in art.hatch_lines(leaf, spacing=3.4):
                stroke(draw, run, GRAPHITE, 1.05, alpha=132)

        stroke(draw, art.ROCK, GRAPHITE, 1.4, alpha=186, closed=True)
        for rib in art.ROCK_RIBS:
            stroke(draw, rib, GRAPHITE, 1.2, alpha=140)
        for index in range(11):
            y = 1168 + index * 12
            stroke(
                draw,
                [(142 + index * 6, y), (296 - index * 3, y + 8)],
                GRAPHITE,
                1.0,
                alpha=104,
            )

    return Image.alpha_composite(panel, on_layer(ops))


# ------------------------------------------------------------------ 水墨


def render_wash():
    """不画轮廓，墨分浓淡：叶根浓、叶尖淡，边缘是化开的。"""
    panel = blank()
    base = Image.new("RGBA", PANEL, (0, 0, 0, 0))

    # 一处极淡的角上气韵
    def mist_ops(draw):
        box = sp([(-40 - 620, 1330 - 430), (-40 + 620, 1330 + 430)])
        draw.ellipse([box[0], box[1]], fill=WASH + (56,))

    base = Image.alpha_composite(base, blur(on_layer(mist_ops), 46))

    # 石头：淡墨铺底 + 柔边，不勾死轮廓
    def rock_ops(draw):
        fill(draw, art.ROCK, WASH, 58)
        for rib in art.ROCK_RIBS:
            stroke(draw, rib, WASH, 3.0, alpha=76)

    base = Image.alpha_composite(base, blur(on_layer(rock_ops), 5))

    # 竹竿：根部浓、梢部淡，用切片叠出纵向渐变
    def culm_ops(draw):
        for culm in art.CULMS:
            for t, quad in art.culm_quads(culm, count=16):
                if max(point[1] for point in quad) < -300:
                    continue
                fill(draw, quad, WASH, int(240 - 190 * t))

    base = Image.alpha_composite(base, blur(on_layer(culm_ops), 1.6))

    # 枝条
    def twig_ops(draw):
        for twig in art.TWIGS:
            stroke(draw, twig["spine"], WASH, 3.4, alpha=150)

    base = Image.alpha_composite(base, blur(on_layer(twig_ops), 2.4))

    # 竹叶：柔边垫底 + 实墨盖面 + 叶根再压一层浓墨
    def halo_ops(draw):
        for leaf in art.LEAVES:
            fill(draw, leaf["outline"], WASH, 74)

    base = Image.alpha_composite(base, blur(on_layer(halo_ops), 7))

    def leaf_ops(draw):
        for leaf in art.LEAVES:
            fill(draw, leaf["outline"], WASH, 118)

    base = Image.alpha_composite(base, blur(on_layer(leaf_ops), 1.2))

    def root_ops(draw):
        for leaf in art.LEAVES:
            count = max(3, int(len(leaf["spine"]) * 0.5))
            outline, _ = art.frame(leaf["spine"][:count], leaf["widths"][:count])
            fill(draw, outline, WASH, 92)

    base = Image.alpha_composite(base, blur(on_layer(root_ops), 1.2))

    # 竹节：墨未干时点的一笔
    def node_ops(draw):
        for mark in art.NODES:
            stroke(draw, mark, WASH, 4.0, alpha=150)

    base = Image.alpha_composite(base, blur(on_layer(node_ops), 3.0))

    def node_core(draw):
        for mark in art.NODES:
            stroke(draw, mark, WASH, 1.8, alpha=180)

    base = Image.alpha_composite(base, on_layer(node_core))

    return Image.alpha_composite(panel, base)


# ------------------------------------------------------------------ 汇总


def main():
    target = pathlib.Path(
        sys.argv[1]
        if len(sys.argv) > 1
        else art.PREVIEW_DIR / "_preview.png"
    )

    panels = [
        ("白描", render_baimiao()),
        ("素描", render_sketch()),
        ("水墨", render_wash()),
    ]

    final = [
        panel.resize((panel.width // SS, panel.height // SS), Image.LANCZOS)
        for _, panel in panels
    ]

    pad, label_h = 14, 34
    width = sum(panel.width for panel in final) + pad * (len(final) + 1)
    height = max(panel.height for panel in final) + pad * 2 + label_h

    sheet = Image.new("RGB", (width, height), (242, 236, 224))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype(LABEL_FONT, 19)

    x = pad
    for (label, _), panel in zip(panels, final):
        draw.text((x + 4, pad), label, fill=INK, font=font)
        sheet.paste(panel.convert("RGB"), (x, pad + label_h))
        x += panel.width + pad

    target.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(target)
    print("已输出 %s  (%d x %d)" % (target, sheet.width, sheet.height))


if __name__ == "__main__":
    main()
