"""按 app.css 里的规则，用 Pillow 合成封面成稿，供本地核对构图。

为什么需要这一步：真实页面的截图会超过工具体积上限（内容一密就超，与页面尺寸无关），
而封面好不好看恰恰只能在成稿里判断。

合成严格照 CSS 走：

    纸张底色  →  画心（按 background-size / background-position 缩放定位，
                     乘以 --cover-art-opacity）
              →  纸色渐隐（按 background-image 的第一层渐变角度近似）
              →  文字（按 tokens 里的字号 / 间距排）

这只是核对用的模拟，不是产物；但参数与 app.css 一一对应，改了 CSS 要同步改这里。

用法：
    python tools/mock_cover.py
"""

import pathlib
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import make_cover_art as art  # noqa: E402
import preview_cover_art as art_png  # noqa: E402

OUT = art.PREVIEW_DIR / "_mock.png"
OUT_DESKTOP = OUT.with_name("_mock-desktop.png")
OUT_MOBILE = OUT.with_name("_mock-mobile.png")

PAPER = (250, 246, 238)
INK = (26, 24, 21)
MUTED = (78, 71, 64)
FAINT = (101, 92, 80)
ACCENT = (163, 46, 34)

SERIF = r"C:\Windows\Fonts\simsun.ttc"
KAI = r"C:\Windows\Fonts\simkai.ttf"
SANS = r"C:\Windows\Fonts\msyh.ttc"

# 与 tokens.css 一致：定版是水墨（白描 / 素描的渲染函数仍可用，只是没在用）
VARIANTS = [
    ("水墨", art_png.render_wash, 0.80),
]

# 与 app.css 的 ::before 一致：(画布宽, 高, 画心高占面板的比例, 水平位置%, 垂直位置%, 渐隐方向)
DESKTOP = (336, 800, 1.08, 52, 100, "down")
MOBILE = (728, 308, 2.35, 100, 46, "right")


def art_tile(renderer, target_w, target_h):
    """把画心渲染成目标尺寸的透明底图。"""
    full = renderer()
    full = full.resize((full.width // art_png.SS, full.height // art_png.SS), Image.LANCZOS)
    return full.resize((max(1, target_w), max(1, target_h)), Image.LANCZOS)


def fade_mask(width, height, direction, solid_until, fade_until):
    """纸色渐隐的 alpha：渐变越往下/往右越透明。"""
    mask = Image.new("L", (width, height), 0)
    pixels = mask.load()

    for y in range(height):
        for x in range(width):
            t = (y / max(1, height - 1)) if direction == "down" else (x / max(1, width - 1))
            if t <= solid_until:
                pixels[x, y] = 255
            elif t >= fade_until:
                pixels[x, y] = 0
            else:
                pixels[x, y] = int(255 * (1 - (t - solid_until) / (fade_until - solid_until)))
    return mask


def compose(renderer, opacity, spec):
    width, height, art_ratio, pos_x, pos_y, direction = spec

    panel = Image.new("RGB", (width, height), PAPER)

    # 画心：按比例缩放后按 background-position 定位，超出部分裁掉
    art_h = int(round(height * art_ratio))
    art_w = int(round(art_h * art.W / art.H))
    tile = art_tile(renderer, art_w, art_h)

    tile = tile.copy()
    alpha = tile.getchannel("A").point(lambda value: int(value * opacity))
    tile.putalpha(alpha)

    left = int(round((width - art_w) * pos_x / 100))
    top = int(round((height - art_h) * pos_y / 100))
    panel.paste(tile, (left, top), tile)

    # 纸色渐隐压在画心上：文字区永远是干净的纸
    if direction == "down":
        mask = fade_mask(width, height, "down", 0.20, 0.58)
    else:
        mask = fade_mask(width, height, "right", 0.34, 0.78)
    panel.paste(Image.new("RGB", (width, height), PAPER), (0, 0), mask)

    return panel


def draw_text(panel, spec):
    """按 tokens 的字号与间距排封面文字。"""
    width, height = spec[0], spec[1]
    draw = ImageDraw.Draw(panel)
    pad_x = int(width * (48 / 336)) if width <= 400 else 24
    y = int(height * (64 / 800)) if height > 400 else 48

    kicker = ImageFont.truetype(SANS, 12)
    headline = ImageFont.truetype(SERIF, 48 if height > 400 else 36)
    body = ImageFont.truetype(SANS, 15)

    draw.text((pad_x, y), "语文素材管理系统", fill=FAINT, font=kicker)
    y += 17 + 12
    draw.text((pad_x, y), "学生登录", fill=INK, font=headline)
    y += (58 if height > 400 else 44) + 24

    draw.rectangle([pad_x, y, pad_x + 64, y + 2], fill=ACCENT)
    y += 2 + 24

    for line in ("账号为 10 位：年级 4 位 + 编号 6 位", "登录状态保存在会话中，退出即失效"):
        draw.text((pad_x + 24, y), line, fill=MUTED, font=body)
        draw.text((pad_x, y), "—", fill=ACCENT, font=body)
        y += 26 + 12


def sheet(spec):
    panels = []
    for label, renderer, opacity in VARIANTS:
        panel = compose(renderer, opacity, spec)
        draw_text(panel, spec)
        panels.append((label, panel))

    pad, label_h = 12, 26
    width = sum(p.width for _, p in panels) + pad * (len(panels) + 1)
    height = max(p.height for _, p in panels) + pad * 2 + label_h
    out = Image.new("RGB", (width, height), (238, 232, 220))
    draw = ImageDraw.Draw(out)
    font = ImageFont.truetype(SANS, 15)

    x = pad
    for label, panel in panels:
        draw.text((x + 2, pad), label, fill=INK, font=font)
        out.paste(panel, (x, pad + label_h))
        x += panel.width + pad

    return out


def main():
    # 两张分开存：合成到一张会宽到 2200 以上，读图时被压缩得看不清细节
    desktop = sheet(DESKTOP)
    mobile = sheet(MOBILE)

    for path, title, image in (
        (OUT_DESKTOP, "宽屏封面（侧栏 21rem × 100dvh）", desktop),
        (OUT_MOBILE, "窄屏封面（通栏 × 内容高）", mobile),
    ):
        out = Image.new("RGB", (image.width, image.height + 26), (238, 232, 220))
        ImageDraw.Draw(out).text(
            (12, 6), title, fill=INK, font=ImageFont.truetype(SANS, 15)
        )
        out.paste(image, (0, 26))
        path.parent.mkdir(parents=True, exist_ok=True)
        out.save(path)
        print("已输出 %s  (%d x %d)" % (path.name, out.width, out.height))


if __name__ == "__main__":
    main()
