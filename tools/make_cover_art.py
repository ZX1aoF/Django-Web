"""生成封面插画：同一幅「竹」，三种技法。

    白描  单线勾勒，不皴不染        cover-baimiao.svg
    素描  铅笔排线，明暗靠线条疏密   cover-sketch.svg
    水墨  墨色晕染，明暗靠墨的浓淡   cover-wash.svg   ← 定版，只出这一张

定版选水墨的道理：白描在封面的实际尺寸下线太细（缩到 336px 宽就快看不见），
素描叠上纸色渐隐后整体发灰；水墨是墨块，缩放后最立得住。
另外两种的渲染函数都留着，跑 --all 可以重出三张再挑。

三张图共用同一份几何（竹竿、竹节、枝条、竹叶、石），渲染方式不同 ——
这样对比的才是技法，不是构图。

几何按传统墨竹的组织方式来，不是把「竹」当几何图形摆 —— 上一版就是栽在这里：
竹叶沿一根直枝等距排开，排出来像麦穗。以下几条是照画谱与画法资料来的：

  竿   弯节不弯竿，太直则僵；三竿**忌平行**，粗细与墨色要有别。
       老竿（粗）墨淡、节距短；新竿（细）墨浓、节距长。
  节   顿笔如铁钉，两端微翘。**各竿的节必须错开** —— 排在一条水平线上就是梯子。
  枝   自节处生发，但要**互生**（左右交替）、**不节节出枝**；枝细而挺，末梢下垂。
  叶   不是一片片排的，是按「个 / 介 / 分 / 重人 / 惊鸦」**成组写**的：
       一组叶起笔聚于一点、叶尖散开（聚如鸡爪，散如凤尾）；
       组内绝不平行（夹角 ≥ 15°）、绝不等长（必有一片主叶，其余缩短）、
       绝不均匀（忌「川」字并列）。
  布叶 下部用「介」压阵（叶密墨重），中部用「分」穿插，上部用「个」收尾
       （叶疏墨淡）；整丛有统一的下垂之势，不能四面开花。
  石   坡石，带皴与苔点，压住画面重心。

几何用折线表达（贝塞尔采样），因此 SVG 与 Pillow 预览能画得完全一致。

用法：
    python tools/make_cover_art.py        # 只输出定版的水墨
    python tools/make_cover_art.py --all  # 三张都出，并写并排预览页
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

# 固定种子。随机抖动只用来打破整齐，必须可复现 —— 否则改了别处会连带把
# 每一片叶的抖动都换掉，就分不清画面变化到底是「这次改对了」还是噪声。
RNG = random.Random(20261017)


# ================================================================ 几何工具


def qbezier(p0, p1, p2, steps):
    """二次贝塞尔采样成折线。"""
    points = []
    for index in range(steps + 1):
        t = index / steps
        u = 1 - t
        points.append(
            (
                u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0],
                u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1],
            )
        )
    return points


def cbezier(p0, p1, p2, p3, steps):
    """三次贝塞尔采样。

    枝条要画成「先斜出、末梢下垂」的转折，二次贝塞尔只有一个弓形，转不出这个弯，
    所以枝条这一层用三次。
    """
    points = []
    for index in range(steps + 1):
        t = index / steps
        u = 1 - t
        points.append(
            (
                u**3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t**3 * p3[0],
                u**3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t**3 * p3[1],
            )
        )
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


def taper(spine, start, end, power=1.0):
    """把一条已采样的中线按 t 从 start 收到 end（power 控制收束曲线）。"""
    total = len(spine)
    widths = [
        start + (end - start) * ((index / (total - 1)) ** power)
        for index in range(total)
    ]
    outline, spine = frame(spine, widths)
    return {"outline": outline, "spine": spine, "widths": widths}


def point_dir_at(shape, t):
    """取形状上 t 处的点、单位切向与宽度。"""
    spine = shape["spine"]
    last = len(spine) - 1
    index = max(1, min(last - 1, int(round(t * last))))
    x, y = spine[index]
    dx = spine[index + 1][0] - spine[index - 1][0]
    dy = spine[index + 1][1] - spine[index - 1][1]
    length = math.hypot(dx, dy) or 1.0
    return x, y, dx / length, dy / length, shape["widths"][index]


def droop_from(direction, amount):
    """把方向朝「正下方」折 amount 度。

    角度体系：0° 指右、90° 指下（SVG 的 y 轴向下）、±180° 指左。
    「下垂」就是让方向更接近 90°，但**不能一律用加减**：
    朝右下（0°）要加，朝左下（-154°）反而要减 —— 两边对称地往 90° 靠。
    所以要取到 90° 的有向角距离，再按符号走。
    """
    direction = (direction + 180) % 360 - 180
    delta = (90 - direction + 180) % 360 - 180
    step = math.copysign(min(abs(delta), amount), delta)
    return (direction + step + 180) % 360 - 180


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
        quads.append((index / (count - 1), [left[a], right[a], right[b], left[b]]))
    return quads


def leaf_width_profile(t, width):
    """叶宽沿叶长的分布。

    竹叶是毛笔一笔点出来的：叶柄细 → 约三成处最宽 → 叶身**缓慢渐细** →
    叶尖出锋。四段来写，关键是第三段。

    早先写成「中段一直保持满宽，到梢部才收」，叶子出来是**两条几乎平行的边**，
    看着像羽毛的羽枝 —— 一组叶排在一起就是一把羽扇。真正让人一眼看出「这是
    竹叶」的，是叶身那道从粗到细的渐收。
    """
    if t < 0.12:
        return width * (0.34 + 0.54 * (t / 0.12) ** 0.7)
    if t < 0.10:
        return width * (0.36 + 0.52 * (t / 0.10) ** 0.7)
    if t < 0.28:
        return width * (0.88 + 0.12 * (t - 0.10) / 0.18)
    if t < 0.62:
        return width * (1.0 - 0.34 * (t - 0.28) / 0.34)
    # 末段收得比看得出来的还要快：线宽本身就占叶宽的一成半，
    # 叶尖若还留着两成宽，描上线就是一个圆头 —— 圆头的叶一定不像竹叶。
    return width * max(0.0, 0.66 * (1 - (t - 0.62) / 0.38) ** 1.35)


def make_leaf(base, angle_deg, length, width, bend):
    """叶片：中线为二次贝塞尔，两侧按叶宽分布收束。

    ``bend`` 沿叶**自身法线**位移，符号全组统一 —— 逆时针看所有叶都朝同一侧弓，
    这才是「被同一个力塑形」。曾经改成统一朝正下方位移，结果是朝下的叶等于没弯、
    朝左右的却弯成弓形，反而更乱：法线本身就是「方向转 90°」，它才是侧向。
    """
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


# ================================================================ 竿


def culm_curve(start, end, bend):
    """由起点、终点与弓量得出二次贝塞尔的控制点。

    注意：曲线只走到控制点的一半远，所以实际弓出的弧度约为给定弓量的一半 ——
    想看到明显弧度就得给足量。
    """
    return (
        start,
        ((start[0] + end[0]) / 2 + bend, (start[1] + end[1]) / 2),
        end,
    )


# 三竿：位置不等距、弓向各异、粗细与墨色分层。
# 「忌平行」—— 等距平行立刻变栅栏；最粗的是老竿（墨淡），最细的是新竿（墨浓）。
CULM_SPECS = [
    # (起点, 终点, 根宽, 梢宽, 弓量, 墨色权重)
    # 竿必须细。原来根宽 31 的时候，三竿合计占到画面宽度的三成，缩到封面尺寸
    # 就是并排三根水泥柱；真实墨竹的竿只占几个百分点，叶反而比竿宽。
    # 主竿向左凸、次竿向右凸，两竿弓成一个「()」—— 有了相向的弧度才不像两根栏杆
    ((196, 1374), (252, -54), 19, 8.5, -128, 0.60),
    ((334, 1374), (300, -22), 12, 5.2, 96, 0.80),
    ((446, 1374), (486, 392), 7, 2.4, -58, 1.00),
]

CULMS = [
    taper(qbezier(*culm_curve(start, end, bend), 56), root_w, tip_w, power=1.0)
    for start, end, root_w, tip_w, bend, _ink in CULM_SPECS
]
CULM_INK = [spec[5] for spec in CULM_SPECS]

# 各竿竹节的相对位置。**每竿都要错开**（这是上一版最显眼的毛病：
# 三条竿的节排在同一水平线上，一眼就是梯子），且同一竿上节距中间大、两头小。
NODE_TS = [
    [0.118, 0.236, 0.362, 0.494, 0.630, 0.760, 0.880, 0.964],
    [0.158, 0.292, 0.428, 0.560, 0.686, 0.802, 0.910],
    [0.208, 0.388, 0.564, 0.732, 0.880],
]


def build_nodes():
    """竹节：一道横过竿身的短弧，两端微翘（「上弯型」节）。"""
    marks = []
    for index, ts in enumerate(NODE_TS):
        for t in ts:
            x, y, dx, dy, width = point_dir_at(CULMS[index], t)
            nx, ny = -dy, dx
            half = width * 0.62
            bow = width * 0.30
            pts = []
            for step in range(7):
                u = step / 6
                offset = -half + 2 * half * u
                lift = bow * (1 - (offset / half) ** 2)
                pts.append((x + nx * offset + dx * lift, y + ny * offset + dy * lift))
            marks.append(pts)
    return marks


NODES = build_nodes()


# ================================================================ 枝与叶

# 竹叶的组合模块。画竹不是一片片画叶，是**一组组写**叶：
# 每一组就是一个汉字结构，起笔聚于一点（叶根），叶尖向不同方向散开。
#   (偏角, 长度系数, 是否主叶)
#
# 关键在「字」本身的结构，而不是把叶均匀铺开：
#   「个」是人字头 + 一竖 —— 一撇一捺大幅张开、两片**交叉**，中间一竖朝下。
#     所以三片叶的开度接近 110°，而不是三片近平行。这是先前最大的误读：
#     把夹角压到 20° 以内，等于把「个」字拆成了三根平行线，一组叶就成了羽枝。
#   「介」是「个」加左右两片张开，四片，中二紧凑、左右舒展。
#   「分」张得最开，常用在丛叶底部或侧边，起展开的作用。
#   「重人」两个人字层叠，用在最密处叠叶。
#   「惊鸦」相反 —— 五六片朝**同一个**方向撇出，是唯一"同向"的模块，表现风势。
# 有了张与不张两种结构，一组一组的叶叠起来才有变化；全都张开就成了棕榈。
LEAF_MODULES = {
    "ge": [(-32, 0.58, False), (0, 1.00, True), (29, 0.54, False)],
    "jie": [(-33, 0.62, False), (-12, 1.00, True), (9, 0.80, False), (31, 0.46, False)],
    "fen": [(-38, 0.68, False), (-13, 1.00, True), (12, 0.72, False), (36, 0.42, False)],
    "chongren": [(-29, 0.96, False), (-9, 1.00, True), (8, 0.82, False), (27, 0.40, False)],
    "jingya": [
        (-20, 1.00, True),
        (-10, 0.68, False),
        (0, 0.50, False),
        (9, 0.72, False),
        (19, 0.42, False),
    ],
}

# 枝条：(竿号, 出枝 t, 出枝角, 枝长, 末梢垂坠角, 主次权重,
#        [(挂点 u, 模块, 叶长, 叶宽), ...])
# 出枝角为负 = 斜向上出；左右交替即「互生」。不是每个节都出枝。
#
# 权重用来分主次：一组丛叶里必须有两三处是「主叶」（叶长、墨浓），其余的作陪衬
# （叶短、墨淡）。13 组叶同样重要、同样清楚、均匀铺满画面 —— 那是图案，不是画。
# 疏密也照这个排：主竿梢部把两组叶都挂在枝梢（0.99 / 0.82），挤成一处密叶；
# 中段与下部各只留一组，空出来。
BRANCHES = [
    # 主竿（最粗、老竿）：这里的「介」与「分」是全画主叶，叶最长
    (0, 0.900, -150, 122, 106, 1.00, [(0.99, "ge", 108, 17), (0.80, "jie", 152, 19)]),
    (0, 0.742, -20, 126, 90, 1.00, [(0.99, "fen", 168, 20)]),
    (0, 0.560, -142, 100, 98, 0.88, [(0.99, "jie", 142, 19)]),
    (0, 0.660, -146, 96, 96, 0.84, [(0.98, "ge", 120, 18)]),
    (0, 0.356, -32, 84, 88, 0.78, [(0.98, "fen", 128, 19)]),
    # 次竿：出枝角刻意不跟主竿严格反着来 —— 左右严格交替会排成一条「蜈蚣」，
    # 真实竹子同一侧连着出两枝是常事
    (1, 0.918, -30, 108, 98, 0.94, [(0.99, "ge", 104, 16), (0.66, "jingya", 136, 18)]),
    (1, 0.845, -34, 92, 94, 0.82, [(0.98, "jie", 118, 18)]),
    (1, 0.752, -158, 100, 100, 0.86, [(0.99, "jie", 130, 18)]),
    (1, 0.572, -36, 88, 92, 0.74, [(0.98, "fen", 120, 18)]),
    (1, 0.398, -150, 74, 86, 0.66, [(0.98, "ge", 108, 17)]),
    # 幼竿（最短、最细）：只作点缀，短而淡
    (2, 0.902, -158, 84, 94, 0.72, [(0.99, "jingya", 112, 16)]),
    (2, 0.636, -22, 70, 88, 0.60, [(0.98, "ge", 96, 15)]),
]


def make_twig(base, angle_deg, length, droop_deg):
    """枝条：细而挺，从节处斜出，末梢因自重下垂。"""
    a1 = math.radians(angle_deg)
    a2 = math.radians(droop_from(angle_deg, droop_deg))
    reach = length * 0.58
    tip = (
        base[0] + math.cos(a1) * reach + math.cos(a2) * (length - reach),
        base[1] + math.sin(a1) * reach + math.sin(a2) * (length - reach),
    )
    p1 = (base[0] + math.cos(a1) * reach * 0.62, base[1] + math.sin(a1) * reach * 0.62)
    p2 = (
        tip[0] - math.cos(a2) * (length - reach) * 0.55,
        tip[1] - math.sin(a2) * (length - reach) * 0.55,
    )
    return taper(cbezier(base, p1, p2, tip, 18), 3.0, 0.6, power=1.3)


def build_leaf_group(
    base, direction_deg, module, length, width, ink, weight=1.0, spread_ratio=None
):
    """按「汉字模块」组织一组叶。

    一组叶共用一个叶根（「起笔聚在一点」），但叶根**不重合**，而且要往两个
    方向错开：

      沿法线  —— 错开才有「凤眼」（叶与叶交叉处的小菱形空隙）；
                 完全重合会成「鼓架」（几线交于一点），错开太小又等于没错开，
                 还是读成从一点放射。
      沿枝反向 —— 叶是沿枝**依次**生出来的（「叶抱枝」），后生的叶根部要往上
                 游退一点，层层叠着才有厚度，否则一组叶是薄薄一片。

    另外整组会给一个偏斜：真实的叶组没有一个是正对称的。
    """
    specs = LEAF_MODULES[module]
    angle = math.radians(direction_deg)
    tangent = (math.cos(angle), math.sin(angle))
    normal = (-tangent[1], tangent[0])
    # 两个错开量都给得很小，是有意的：
    #   「起笔聚在一点」是组叶的根本，叶根一散开，一组叶就变成几片平行排列的
    #   独立叶（远看是羽扇）。曾经把沿枝退开给到 45px 求「层次」，恰恰毁掉的就是
    #   这个「聚」。层次靠浓淡和前后覆盖，不靠把根拉开。
    spread = length * (0.05 if spread_ratio is None else spread_ratio)
    skew = RNG.uniform(-6.0, 6.0)
    len_scale = 0.72 + 0.28 * weight

    leaves = []
    for order, (offset, scale, hero) in enumerate(specs):
        shift = (order - (len(specs) - 1) / 2) * spread
        back = order * length * 0.025
        root = (
            base[0] + normal[0] * shift - tangent[0] * back,
            base[1] + normal[1] * shift - tangent[1] * back,
        )
        jitter = 0.90 + 0.20 * RNG.random()
        width_jitter = 0.74 + 0.44 * RNG.random()
        leaves.append(
            make_leaf(
                root,
                direction_deg + offset + skew,
                length * scale * jitter * len_scale,
                width * width_jitter * (1.0 if hero else 0.88),
                # 叶身要有一点弧。给太小是一片直刀片，给太大就成弓了
                length * (0.24 if hero else 0.16) * scale,
            )
        )
        leaves[-1]["ink"] = ink if hero else ink * 0.68
        leaves[-1]["hero"] = hero
        leaves[-1]["module"] = module

    return leaves


def build_branches():
    twigs, leaves, groups = [], [], []
    for culm_index, t, angle, twig_len, droop, weight, specs in BRANCHES:
        x, y, _, _, _ = point_dir_at(CULMS[culm_index], t)
        twig = make_twig((x, y), angle, twig_len, droop)
        twig["ink"] = CULM_INK[culm_index]
        twigs.append(twig)

        for anchor, module, leaf_len, leaf_w in specs:
            gx, gy, gdx, gdy, _ = point_dir_at(twig, anchor)
            twig_dir = math.degrees(math.atan2(gdy, gdx))
            # 叶比枝更垂：竹叶从枝上生出后向下垂，所以主方向再往正下方折一点
            direction = droop_from(twig_dir, 30)
            group = build_leaf_group(
                (gx, gy),
                direction,
                module,
                leaf_len,
                leaf_w,
                CULM_INK[culm_index],
                weight,
            )
            groups.append(group)
            leaves += group
    return twigs, leaves, groups


TWIGS, LEAVES, GROUPS = build_branches()


# ================================================================ 石

# 坡石：低伏，顶部要有起伏与折角。做成平滑的圆弧就成了一个灰面包
ROCK = [
    (62, 1312), (70, 1272), (94, 1238), (126, 1226), (148, 1244),
    (176, 1222), (202, 1200), (230, 1212), (262, 1238), (296, 1226),
    (328, 1258), (340, 1300), (334, 1312),
]
# 皴：几道顺着石势的短线，表现体积
ROCK_RIBS = [
    [(92, 1312), (104, 1268), (130, 1236)],
    [(168, 1312), (178, 1272), (200, 1238)],
    [(250, 1312), (258, 1274), (280, 1246)],
    [(306, 1306), (312, 1276), (326, 1256)],
]
# 苔点：石上点苔，聚散不均。半径 2~3.4 —— 缩到封面尺寸后，再大就是一把黑芝麻
MOSS_SPECS = [
    (108, 1244, 3.2), (134, 1228, 2.4), (160, 1252, 3.0), (190, 1232, 2.2),
    (218, 1246, 2.8), (248, 1240, 2.2), (88, 1280, 2.6), (288, 1268, 2.6),
]


def build_moss():
    """苔点：每点画成略不规则的小团，避免成排等大 —— 成排就变成珠子。"""
    spots = []
    for cx, cy, radius in MOSS_SPECS:
        points = []
        for step in range(8):
            angle = step / 8 * math.tau
            wobble = 0.74 + 0.46 * RNG.random()
            points.append(
                (cx + math.cos(angle) * radius * wobble, cy + math.sin(angle) * radius * wobble)
            )
        spots.append(points)
    return spots


MOSS = build_moss()


# ================================================================ SVG 输出


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
            '<path d="%s" stroke="%s" stroke-width="1.9" stroke-linecap="round"/>'
            % (d_of(twig["spine"]), INK)
        )

    for mark in NODES:
        parts.append(
            '<path d="%s" stroke="%s" stroke-width="2.4" stroke-linecap="round"/>'
            % (d_of(mark), INK)
        )

    for leaf in LEAVES:
        parts.append(
            '<path d="%s" stroke="%s" stroke-width="1.9" stroke-linejoin="round"/>'
            % (d_of(leaf["outline"], closed=True), INK)
        )
        # 白描里也勾一根主脉
        parts.append(
            '<path d="%s" stroke="%s" stroke-width="1.0" stroke-linecap="round" opacity="0.45"/>'
            % (d_of(leaf["spine"]), INK)
        )

    parts.append(
        '<path d="%s" stroke="%s" stroke-width="2.4" stroke-linejoin="round"/>'
        % (d_of(ROCK, closed=True), INK)
    )
    for rib in ROCK_RIBS:
        parts.append(
            '<path d="%s" stroke="%s" stroke-width="1.6" stroke-linecap="round"/>'
            % (d_of(rib), INK)
        )
    for spot in MOSS:
        parts.append(
            '<path d="%s" fill="%s" opacity="0.85"/>' % (d_of(spot, closed=True), INK)
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
        for line in hatch_lines(culm, spacing=6.4):
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
        # 主叶描得重一些：一组叶里总要有浓淡，否则读成一片
        weight = 0.78 if leaf["hero"] else 0.5
        parts.append(
            '<path d="%s" stroke="%s" stroke-width="1.2" opacity="%.2f" stroke-linejoin="round"/>'
            % (d_of(leaf["outline"], closed=True), GRAPHITE, weight)
        )
        for line in hatch_lines(leaf, spacing=3.6):
            parts.append(
                '<path d="%s" stroke="%s" stroke-width="1.05" stroke-linecap="round" opacity="%.2f"/>'
                % (d_of(line), GRAPHITE, 0.44 * weight + 0.14)
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
    # 石面的稀疏排线
    for index in range(9):
        y = 1180 + index * 13
        parts.append(
            '<path d="M %d %d L %d %d" stroke="%s" stroke-width="1" opacity="0.3"/>'
            % (138 + index * 5, y, 300 - index * 4, y + 9, GRAPHITE)
        )
    for spot in MOSS:
        parts.append(
            '<path d="%s" fill="%s" opacity="0.5"/>' % (d_of(spot, closed=True), GRAPHITE)
        )

    return svg_document("\n".join(parts))


WASH_DEFS = """
<linearGradient id="inkLeaf" x1="0.1" y1="0" x2="0.5" y2="1">
  <stop offset="0" stop-color="%(w)s" stop-opacity="0.98"/>
  <stop offset="0.45" stop-color="%(w)s" stop-opacity="0.88"/>
  <stop offset="1" stop-color="%(w)s" stop-opacity="0.58"/>
</linearGradient>
<linearGradient id="inkCulm" x1="0" y1="0" x2="0" y2="1">
  <stop offset="0" stop-color="%(w)s" stop-opacity="0.22"/>
  <stop offset="0.45" stop-color="%(w)s" stop-opacity="0.70"/>
  <stop offset="1" stop-color="%(w)s" stop-opacity="0.96"/>
</linearGradient>
<filter id="soft" x="-40%%" y="-40%%" width="180%%" height="180%%">
  <feGaussianBlur stdDeviation="6"/>
</filter>
""" % {"w": WASH}


def render_wash():
    """水墨：不画轮廓。墨分浓淡 —— 老竿淡、新竿浓；一组叶里主叶浓、衬叶淡。

    弃用了「角上一团雾」的老做法：那团东西不论调多淡，在封面那个尺寸下都会
    读成一块灰斑，而写意最讲留白。
    """
    parts = []

    # 石头：淡墨铺底 + 柔边收体积；再压一道不模糊的边，否则会糊成一团灰
    parts.append(
        '<path d="%s" fill="%s" opacity="0.08" filter="url(#soft)"/>'
        % (d_of(ROCK, closed=True), WASH)
    )
    parts.append(
        '<path d="%s" stroke="%s" stroke-width="1.5" opacity="0.20" stroke-linejoin="round"/>'
        % (d_of(ROCK, closed=True), WASH)
    )
    for rib in ROCK_RIBS:
        parts.append(
            '<path d="%s" stroke="%s" stroke-width="2.6" opacity="0.34" stroke-linecap="round" filter="url(#soft)"/>'
            % (d_of(rib), WASH)
        )

    # 竹竿：淡墨。墨竹的浓淡关系是「竿淡叶浓」，早先竿给到 0.4~1.0，
    # 缩到封面尺寸就跟叶一个分量，整片糊成三根灰柱子。
    for culm, ink in zip(CULMS, CULM_INK):
        parts.append(
            '<path d="%s" fill="url(#inkCulm)" opacity="%.2f"/>'
            % (d_of(clip_above(culm["outline"]), closed=True), 0.34 + 0.30 * ink)
        )

    for twig in TWIGS:
        parts.append(
            '<path d="%s" stroke="%s" stroke-width="3.2" opacity="%.2f" stroke-linecap="round" filter="url(#soft)"/>'
            % (d_of(twig["spine"]), WASH, 0.34 + 0.36 * twig["ink"])
        )

    # 竹叶：柔边垫底 + 实墨盖面，浓度按该叶的墨色权重（主叶浓、衬叶淡）。
    # 这里是全画的「浓」：缩到封面尺寸后，叶仍要是明显的墨块，不能只剩一片灰。
    for leaf in LEAVES:
        parts.append(
            '<path d="%s" fill="%s" opacity="%.2f" filter="url(#soft)"/>'
            % (d_of(leaf["outline"], closed=True), WASH, 0.24 * leaf["ink"])
        )
    for leaf in LEAVES:
        parts.append(
            '<path d="%s" fill="url(#inkLeaf)" opacity="%.2f"/>'
            % (d_of(leaf["outline"], closed=True), 0.72 + 0.28 * leaf["ink"])
        )

    # 竹节：墨未干时点的一笔
    for mark in NODES:
        parts.append(
            '<path d="%s" stroke="%s" stroke-width="4" opacity="0.5" stroke-linecap="round" filter="url(#soft)"/>'
            % (d_of(mark), WASH)
        )
    for mark in NODES:
        parts.append(
            '<path d="%s" stroke="%s" stroke-width="1.7" opacity="0.66" stroke-linecap="round"/>'
            % (d_of(mark), WASH)
        )

    # 苔点：浓墨点醒
    for spot in MOSS:
        parts.append(
            '<path d="%s" fill="%s" opacity="0.48"/>' % (d_of(spot, closed=True), WASH)
        )

    return svg_document("\n".join(parts), WASH_DEFS)


# ================================================================ 预览页


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
    parser.add_argument(
        "--all",
        action="store_true",
        help="连同白描、素描一起输出并写并排预览页（默认只出定版的水墨）",
    )
    options = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    renderers = {
        "cover-wash.svg": render_wash,
        "cover-baimiao.svg": render_baimiao,
        "cover-sketch.svg": render_sketch,
    }
    names = list(renderers) if options.all else ["cover-wash.svg"]

    for name in names:
        content = renderers[name]()
        path = OUT_DIR / name
        path.write_text(content, encoding="utf-8")
        print("  %-22s %6.1f KB" % (name, len(content.encode("utf-8")) / 1024))

    print(
        "  竹竿 %d 根 / 竹节 %d 处 / 枝条 %d 支 / 叶组 %d 组 / 竹叶 %d 片 / 苔点 %d 处"
        % (len(CULMS), len(NODES), len(TWIGS), len(GROUPS), len(LEAVES), len(MOSS))
    )

    if options.all:
        write_previews(PREVIEW_DIR)


if __name__ == "__main__":
    main()
