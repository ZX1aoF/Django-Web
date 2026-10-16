"""生成封面插画：同一幅「竹」，三种技法。

    白描  单线勾勒，不皴不染        cover-baimiao.svg
    素描  铅笔排线，明暗靠线条疏密   cover-sketch.svg
    水墨  墨色晕染，明暗靠墨的浓淡   cover-wash.svg

三张图共用同一份几何（竹竿、竹节、枝条、竹叶、石），渲染方式不同 ——
这样对比的才是技法，不是构图。

几何要点（照着真实竹子画的，不是几何装饰）：
  - 竹叶长在**枝条**上，沿枝条分布、朝向大致一致；不是从一点呈扇形散开
  - 竹竿有弯曲，不是垂直线
  - 竹节是一道横笔，略宽于竿

几何用折线表达（贝塞尔采样），因此 SVG 与 Pillow 预览能画得完全一致。

用法：
    python tools/make_cover_art.py            # 写入 static/img/
    python tools/make_cover_art.py --preview  # 额外输出并排预览页
"""

import argparse
import math
import pathlib
import random

# 画布：竖构图。封面是竖长条，比例取 1 : 2.46
W, H = 520, 1280

INK = "#1A1815"
GRAPHITE = "#6E6659"
WASH = "#2A2620"

OUT_DIR = pathlib.Path(__file__).resolve().parent.parent / "static" / "img"
# 预览产物放在仓库外：它们是核对用的，不该进版本库
PREVIEW_DIR = OUT_DIR.parents[2] / "design-compare" / "art"

RNG = random.Random(20261016)


# ---------------------------------------------------------------- 几何工具


def qbezier(p0, p1, p2, steps):
    """二次贝塞尔采样成折线。"""
    points = []
    for index in range(steps + 1):
        t = index / steps
        u = 1 - t
        x = u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0]
        y = u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1]
        points.append((x, y))
    return points


def normals(spine):
    """逐点法线（由相邻点差分求得，所以弯曲中线也能得到平滑轮廓）。"""
    result = []
    count = len(spine)
    for index, (x, y) in enumerate(spine):
        if index == 0:
            dx, dy = spine[1][0] - x, spine[1][1] - y
        elif index == count - 1:
            dx, dy = x - spine[-2][0], y - spine[-2][1]
        else:
            dx = spine[index + 1][0] - spine[index - 1][0]
            dy = spine[index + 1][1] - spine[index - 1][1]
        length = math.hypot(dx, dy) or 1.0
        result.append((-dy / length, dx / length))
    return result


def frame(spine, widths):
    """把中线按逐点半宽扩成闭合轮廓。"""
    axes = normals(spine)
    left, right = [], []
    for (x, y), (nx, ny), width in zip(spine, axes, widths):
        half = width / 2
        left.append((x + nx * half, y + ny * half))
        right.append((x - nx * half, y - ny * half))
    return left + right[::-1], spine


def tapered(points, start, end, power=1.0, steps=48):
    """按 t 从 start 线性收到 end（power 控制收束曲线）。

    注意 widths 的长度必须与采样出的中线点数一致 —— 贝塞尔采样 steps 步会得到
    steps + 1 个点，少一个就会在后面按点取宽度时越界。
    """
    spine = qbezier(points[0], points[1], points[2], max(2, steps))
    total = len(spine)
    widths = [
        start + (end - start) * ((index / (total - 1)) ** power)
        for index in range(total)
    ]
    outline, spine = frame(spine, widths)
    return {"outline": outline, "spine": spine, "widths": widths}


def leaf_width_profile(t, width):
    """叶宽沿叶长的分布。

    真实竹叶不是两头尖的柳叶刀：根部略窄、约两成处最宽，然后一路收到尖。
    早先用 (1-t)^0.62 导致最宽处落在叶根、收得太快，画出来像箭头。

    clamp 不能省：t 取到 1 时浮点误差会让底数变成 -1e-16，
    负数开分数次方在 Python 里得到复数，坐标就废了。
    """
    if t < 0.18:
        return width * (0.62 + 0.38 * (t / 0.18) ** 0.7)
    return width * max(0.0, 1 - (t - 0.18) / 0.82) ** 0.55


def make_leaf(base, angle_deg, length, width, bend):
    """叶片：中线为二次贝塞尔，两侧按叶宽分布收束。"""
    angle = math.radians(angle_deg)
    tip = (base[0] + math.cos(angle) * length, base[1] + math.sin(angle) * length)
    mid = ((base[0] + tip[0]) / 2, (base[1] + tip[1]) / 2)
    nx, ny = -math.sin(angle), math.cos(angle)
    control = (mid[0] + nx * bend, mid[1] + ny * bend)

    spine = qbezier(base, control, tip, 18)
    widths = [
        leaf_width_profile(index / (len(spine) - 1), width)
        for index in range(len(spine))
    ]
    outline, spine = frame(spine, widths)
    return {"outline": outline, "spine": spine, "widths": widths}


def point_at(shape, t):
    """取任意形状上 t（0 起 → 1 终）处的点与走向。"""
    spine = shape["spine"]
    index = max(1, min(len(spine) - 2, round(t * (len(spine) - 1))))
    x, y = spine[index]
    dx, dy = x - spine[index - 1][0], y - spine[index - 1][1]
    length = math.hypot(dx, dy) or 1.0
    return x, y, dx / length, dy / length, shape["widths"][index]


def culm_quads(culm, count=16):
    """把竹竿切成若干小四边形，便于按位置施加浓淡（PNG 预览用）。"""
    spine, widths = culm["spine"], culm["widths"]
    axes = normals(spine)
    left, right = [], []
    for (x, y), (nx, ny), width in zip(spine, axes, widths):
        half = width / 2
        left.append((x + nx * half, y + ny * half))
        right.append((x - nx * half, y - ny * half))

    last = len(spine) - 1
    quads = []
    for index in range(count):
        a = int(index * last / count)
        b = int((index + 1) * last / count)
        if b <= a:
            continue
        quads.append(
            (index / (count - 1), [left[a], right[a], right[b], left[b]])
        )
    return quads


# ---------------------------------------------------------------- 构图

# 三竿竹：左粗右细，都有弯曲；梢部顶出画面，是折枝式构图
CULM_SPECS = [
    ((226, 1340), (168, -90), 32, 17, -128),
    ((352, 1340), (348, -70), 20, 11, 74),
    ((444, 1340), (492, 320), 12, 4, 96),
]

def culm_curve(start, end, bend):
    """由起点、终点与弯曲量得出二次贝塞尔的控制点。"""
    return (
        start,
        ((start[0] + end[0]) / 2 + bend, (start[1] + end[1]) / 2),
        end,
    )


CULMS = [
    tapered(culm_curve(start, end, bend), width_base, width_tip, power=0.9)
    for start, end, width_base, width_tip, bend in CULM_SPECS
]

# 枝条 + 叶丛：(竹竿序号, t, 枝条角度, 枝条长, 叶数, 展开角, 叶长, 叶宽, 弯曲)
# 叶数刻意压到 3~5、展开角收到 50° 以内：叶片一多、一散，就会互相穿插成一团
CLUSTER_SPECS = [
    (0, 0.93, -150, 104, 5, 50, 156, 20, 40),
    (0, 0.80, -22, 104, 5, 48, 164, 21, 42),
    (0, 0.63, -142, 92, 4, 46, 148, 19, 36),
    (0, 0.48, -30, 88, 4, 46, 142, 19, 34),
    (0, 0.30, -136, 82, 4, 44, 132, 18, 30),
    (0, 0.16, -24, 76, 4, 44, 124, 17, 28),
    (1, 0.95, -44, 96, 4, 48, 156, 19, 38),
    (1, 0.80, -146, 88, 4, 46, 144, 19, 34),
    (1, 0.62, -34, 84, 4, 46, 138, 18, 32),
    (1, 0.42, -140, 78, 3, 42, 126, 17, 28),
    (2, 0.96, -18, 84, 4, 46, 142, 18, 32),
    (2, 0.70, -152, 78, 4, 44, 130, 17, 30),
    (2, 0.42, -28, 72, 3, 42, 118, 16, 26),
]

# 石头：低矮的坡石。顶部不能起尖角，否则会读成屋顶
ROCK = [
    (74, 1310), (82, 1226), (110, 1180), (152, 1158), (196, 1166),
    (236, 1188), (284, 1182), (322, 1218), (334, 1272), (326, 1310),
]
ROCK_RIBS = [
    [(108, 1310), (120, 1250), (146, 1200)],
    [(180, 1310), (190, 1256), (214, 1214)],
    [(262, 1310), (270, 1262), (292, 1228)],
]


def make_twig(base, angle_deg, length, bend):
    """枝条：细，梢部更细。竹叶就挂在枝条上。"""
    angle = math.radians(angle_deg)
    tip = (base[0] + math.cos(angle) * length, base[1] + math.sin(angle) * length)
    mid = ((base[0] + tip[0]) / 2, (base[1] + tip[1]) / 2)
    nx, ny = -math.sin(angle), math.cos(angle)
    control = (mid[0] + nx * bend, mid[1] + ny * bend)
    return tapered((base, control, tip), 3.2, 0.9, power=1.0, steps=14)


def build_clusters():
    bundles = []
    for culm_index, t, angle, twig_len, count, spread, leaf_len, leaf_w, bend in CLUSTER_SPECS:
        x, y, _, _, _ = point_at(CULMS[culm_index], t)
        twig = make_twig((x, y), angle, twig_len, bend)

        leaves = []
        for order in range(count):
            # 叶子集中在枝条外段，且**弯曲方向一致**、展开角有限 ——
            # 这样它们像一把折扇叠着，而不是互相穿插
            u = 0.42 + 0.58 * (order / max(1, count - 1))
            bx, by, _, _, _ = point_at(twig, u)
            offset = -spread / 2 + spread * (order / max(1, count - 1))
            scale = 1.0 - 0.24 * (order / max(1, count - 1))
            leaves.append(
                make_leaf(
                    (bx, by),
                    angle + offset,
                    leaf_len * scale * (0.9 + 0.2 * RNG.random()),
                    leaf_w * scale * (0.9 + 0.2 * RNG.random()),
                    36,
                )
            )
        bundles.append((twig, leaves))
    return bundles


CLUSTERS = build_clusters()
LEAVES = [leaf for _, leaves in CLUSTERS for leaf in leaves]
TWIGS = [twig for twig, _ in CLUSTERS]


def build_nodes():
    marks = []
    for culm_index, spec in enumerate(CULM_SPECS):
        for t in (0.18, 0.34, 0.50, 0.66, 0.80, 0.92):
            x, y, dx, dy, width = point_at(CULMS[culm_index], t)
            nx, ny = -dy, dx
            half = width * 0.66
            marks.append(
                [(x + nx * half, y + ny * half), (x - nx * half, y - ny * half)]
            )
    return marks


NODES = build_nodes()


# ---------------------------------------------------------------- SVG 输出


def d_of(points, closed=False):
    parts = ["M%.1f %.1f" % points[0]]
    parts += ["L%.1f %.1f" % point for point in points[1:]]
    if closed:
        parts.append("Z")
    return " ".join(parts)


def clip_above(points, limit=-300):
    return [point for point in points if point[1] > limit]


def svg_document(body, extra_defs=""):
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" '
        'width="%d" height="%d" fill="none">\n'
        "<defs>%s</defs>\n%s\n</svg>\n"
    ) % (W, H, W, H, extra_defs, body)


def render_baimiao():
    """白描：只有线，粗细一致，不皴不染。"""
    parts = []

    for culm in CULMS:
        parts.append(
            '<path d="%s" stroke="%s" stroke-width="2.6" stroke-linejoin="round"/>'
            % (d_of(clip_above(culm["outline"]), closed=True), INK)
        )

    for twig in TWIGS:
        parts.append(
            '<path d="%s" stroke="%s" stroke-width="2.0" stroke-linecap="round"/>'
            % (d_of(twig["spine"]), INK)
        )

    for mark in NODES:
        parts.append(
            '<path d="%s" stroke="%s" stroke-width="2.5" stroke-linecap="round"/>'
            % (d_of(mark), INK)
        )

    for leaf in LEAVES:
        parts.append(
            '<path d="%s" stroke="%s" stroke-width="2.0" stroke-linejoin="round"/>'
            % (d_of(leaf["outline"], closed=True), INK)
        )
        # 叶脉：白描里也会勾一根主脉
        parts.append(
            '<path d="%s" stroke="%s" stroke-width="1.1" stroke-linecap="round" opacity="0.5"/>'
            % (d_of(leaf["spine"]), INK)
        )

    parts.append(
        '<path d="%s" stroke="%s" stroke-width="2.4" stroke-linejoin="round"/>'
        % (d_of(ROCK, closed=True), INK)
    )
    for rib in ROCK_RIBS:
        parts.append(
            '<path d="%s" stroke="%s" stroke-width="1.7" stroke-linecap="round"/>'
            % (d_of(rib), INK)
        )

    return svg_document("\n".join(parts))


def hatch_lines(shape, spacing):
    """沿中线做平行排线的折线数据。

    线长随该处半宽自然收短，所以叶尖附近的排线会自己消失。
    返回折线列表（不是 SVG 字符串），SVG 与 PNG 两条渲染路径共用。
    """
    spine, widths = shape["spine"], shape["widths"]
    axes = normals(spine)
    max_half = max(widths) / 2
    lines = []

    offset = spacing
    while offset < max_half - spacing * 0.3:
        run = []
        for index, (x, y) in enumerate(spine):
            if widths[index] / 2 < offset:
                if len(run) >= 2:
                    lines.append(run)
                run = []
                continue
            nx, ny = axes[index]
            run.append((x + nx * offset, y + ny * offset))
        if len(run) >= 2:
            lines.append(run)

        offset += spacing

    return lines


def render_sketch():
    """素描：轮廓轻、排线密，明暗全由线条疏密表达。"""
    parts = []

    for culm in CULMS:
        outline = clip_above(culm["outline"])
        for offset, alpha in ((0, 0.7), (1.5, 0.34)):
            shifted = [(x + offset, y + offset * 0.6) for x, y in outline]
            parts.append(
                '<path d="%s" stroke="%s" stroke-width="1.3" opacity="%.2f" stroke-linejoin="round"/>'
                % (d_of(shifted, closed=True), GRAPHITE, alpha)
            )
        for line in hatch_lines(culm, spacing=6.0):
            parts.append(
                '<path d="%s" stroke="%s" stroke-width="1.05" stroke-linecap="round" opacity="0.42"/>'
                % (d_of(line), GRAPHITE)
            )

    for twig in TWIGS:
        parts.append(
            '<path d="%s" stroke="%s" stroke-width="1.2" opacity="0.66" stroke-linecap="round"/>'
            % (d_of(twig["spine"]), GRAPHITE)
        )

    for mark in NODES:
        parts.append(
            '<path d="%s" stroke="%s" stroke-width="1.6" opacity="0.62" stroke-linecap="round"/>'
            % (d_of(mark), GRAPHITE)
        )

    for leaf in LEAVES:
        parts.append(
            '<path d="%s" stroke="%s" stroke-width="1.2" opacity="0.68" stroke-linejoin="round"/>'
            % (d_of(leaf["outline"], closed=True), GRAPHITE)
        )
        for line in hatch_lines(leaf, spacing=3.8):
            parts.append(
                '<path d="%s" stroke="%s" stroke-width="1.05" stroke-linecap="round" opacity="0.42"/>'
                % (d_of(line), GRAPHITE)
            )

    parts.append(
        '<path d="%s" stroke="%s" stroke-width="1.4" opacity="0.68" stroke-linejoin="round"/>'
        % (d_of(ROCK, closed=True), GRAPHITE)
    )
    for rib in ROCK_RIBS:
        parts.append(
            '<path d="%s" stroke="%s" stroke-width="1.2" opacity="0.5" stroke-linecap="round"/>'
            % (d_of(rib), GRAPHITE)
        )
    for index in range(10):
        y = 1176 + index * 12
        parts.append(
            '<path d="M %d %d L %d %d" stroke="%s" stroke-width="1" opacity="0.34"/>'
            % (146 + index * 5, y, 292 - index * 3, y + 8, GRAPHITE)
        )

    return svg_document("\n".join(parts))


WASH_DEFS = """
<linearGradient id="inkLeaf" x1="0.1" y1="0" x2="0.5" y2="1">
  <stop offset="0" stop-color="%(w)s" stop-opacity="0.86"/>
  <stop offset="0.45" stop-color="%(w)s" stop-opacity="0.56"/>
  <stop offset="1" stop-color="%(w)s" stop-opacity="0.16"/>
</linearGradient>
<linearGradient id="inkCulm" x1="0" y1="0" x2="0" y2="1">
  <stop offset="0" stop-color="%(w)s" stop-opacity="0.26"/>
  <stop offset="0.5" stop-color="%(w)s" stop-opacity="0.72"/>
  <stop offset="1" stop-color="%(w)s" stop-opacity="0.96"/>
</linearGradient>
<radialGradient id="inkMist" cx="0.5" cy="0.5" r="0.5">
  <stop offset="0" stop-color="%(w)s" stop-opacity="0.34"/>
  <stop offset="1" stop-color="%(w)s" stop-opacity="0"/>
</radialGradient>
<filter id="soft" x="-40%%" y="-40%%" width="180%%" height="180%%">
  <feGaussianBlur stdDeviation="7"/>
</filter>
<filter id="softer" x="-60%%" y="-60%%" width="220%%" height="220%%">
  <feGaussianBlur stdDeviation="46"/>
</filter>
""" % {"w": WASH}


def render_wash():
    """水墨：不画轮廓。墨分浓淡 —— 叶根浓、叶尖淡，边缘是化开的。"""
    parts = []

    # 一处极淡的角上气韵，只作衬托。面积必须大到读不出形状，
    # 否则会被看成两团云 —— 上一版就踩过这个坑
    parts.append(
        '<ellipse cx="-40" cy="1330" rx="620" ry="430" fill="url(#inkMist)" opacity="0.55" filter="url(#softer)"/>'
    )

    # 石头：淡墨铺底 + 柔边收出体积，再压一道稍实的边，免得糊成一团
    parts.append(
        '<path d="%s" fill="%s" opacity="0.2" filter="url(#soft)"/>'
        % (d_of(ROCK, closed=True), WASH)
    )
    parts.append(
        '<path d="%s" stroke="%s" stroke-width="2.6" opacity="0.32" stroke-linejoin="round" filter="url(#soft)"/>'
        % (d_of(ROCK, closed=True), WASH)
    )
    for rib in ROCK_RIBS:
        parts.append(
            '<path d="%s" stroke="%s" stroke-width="3.2" opacity="0.42" stroke-linecap="round" filter="url(#soft)"/>'
            % (d_of(rib), WASH)
        )

    # 竹竿：纵向渐变，根部浓、梢部淡
    for culm in CULMS:
        parts.append(
            '<path d="%s" fill="url(#inkCulm)"/>'
            % d_of(clip_above(culm["outline"]), closed=True)
        )

    for twig in TWIGS:
        parts.append(
            '<path d="%s" stroke="%s" stroke-width="3.4" opacity="0.6" stroke-linecap="round" filter="url(#soft)"/>'
            % (d_of(twig["spine"]), WASH)
        )

    # 竹叶：柔边垫底 + 实墨盖面，边缘自然化开
    for leaf in LEAVES:
        path = d_of(leaf["outline"], closed=True)
        parts.append(
            '<path d="%s" fill="%s" opacity="0.3" filter="url(#soft)"/>' % (path, WASH)
        )
    for leaf in LEAVES:
        parts.append(
            '<path d="%s" fill="url(#inkLeaf)"/>' % d_of(leaf["outline"], closed=True)
        )

    # 竹节：墨未干时点的一笔
    for mark in NODES:
        parts.append(
            '<path d="%s" stroke="%s" stroke-width="4" opacity="0.55" stroke-linecap="round" filter="url(#soft)"/>'
            % (d_of(mark), WASH)
        )
    for mark in NODES:
        parts.append(
            '<path d="%s" stroke="%s" stroke-width="1.8" opacity="0.7" stroke-linecap="round"/>'
            % (d_of(mark), WASH)
        )

    return svg_document("\n".join(parts), WASH_DEFS)


# ---------------------------------------------------------------- 预览页


def write_previews(directory):
    page = [
        '<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">',
        "<title>封面插画预览</title><style>",
        "body{margin:0;display:flex;background:#F2ECE0;"
        "font:13px/1.6 -apple-system,'Microsoft YaHei',sans-serif;color:#4E4740}",
        # 必须有 min-width:0：否则 img 的固有宽度会把 flex 项撑开，页面会被拉到 1600px 宽
        "figure{margin:0;padding:8px;flex:1 1 0;min-width:0;text-align:center}",
        "img{display:block;width:100%;height:auto;border:1px solid #DCD2BE;background:#FAF6EE}",
        "figcaption{padding-top:6px}",
        "</style></head><body>",
    ]

    for name, label in (("baimiao", "白描"), ("sketch", "素描"), ("wash", "水墨")):
        page.append(
            '<figure><img src="%s" alt="%s"><figcaption>%s</figcaption></figure>'
            % ("cover-%s.svg" % name, label, label)
        )

    page.append("</body></html>")
    (directory / "_preview.html").write_text("\n".join(page), encoding="utf-8")
    print("  预览页：%s" % (directory / "_preview.html"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview", action="store_true", help="额外输出并排预览页")
    options = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    outputs = {
        "cover-baimiao.svg": render_baimiao(),
        "cover-sketch.svg": render_sketch(),
        "cover-wash.svg": render_wash(),
    }

    for name, content in outputs.items():
        path = OUT_DIR / name
        path.write_text(content, encoding="utf-8")
        print("  %-22s %6.1f KB" % (name, len(content.encode("utf-8")) / 1024))

    print(
        "  竹竿 %d 根 / 枝条 %d 支 / 竹叶 %d 片 / 竹节 %d 处"
        % (len(CULMS), len(TWIGS), len(LEAVES), len(NODES))
    )

    if options.preview:
        write_previews(PREVIEW_DIR)


if __name__ == "__main__":
    main()
