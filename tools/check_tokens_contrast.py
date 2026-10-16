"""校验 tokens.css 里的配色是否满足 WCAG 2.1 AA 对比度。

技能要求「Verify contrast programmatically, not by eye」，这个脚本就是那个校验。

用法：
    python check_tokens_contrast.py <tokens.css> [选择器]

    选择器默认 :root。主题块（如 [data-theme="light"]）会先铺 :root 再覆盖，
    与 CSS 的层叠一致。

判断标准：
    正文 / 小字       >= 4.5:1
    大字号(>=24px)    >= 3:1
    控件边界、状态点  >= 3:1
"""

import pathlib
import re
import sys

# (说明, 前景 token, 背景 token, 最低比值)
CHECKS = [
    ("正文 / 页面底色", "text", "bg", 4.5),
    ("次级文字 / 页面底色", "text-muted", "bg", 4.5),
    ("弱化文字 / 页面底色", "text-faint", "bg", 4.5),
    ("正文 / 卡片底色", "text", "card-bg", 4.5),
    ("次级文字 / 卡片底色", "text-muted", "card-bg", 4.5),
    ("弱化文字 / 卡片底色", "text-faint", "card-bg", 4.5),
    ("正文 / 次级底色", "text", "surface-2", 4.5),
    ("次级文字 / 次级底色", "text-muted", "surface-2", 4.5),
    ("弱化文字 / 次级底色", "text-faint", "surface-2", 4.5),
    ("链接色 / 页面底色", "accent", "bg", 4.5),
    ("链接色 / 卡片底色", "accent", "card-bg", 4.5),
    ("副色文字 / 页面底色", "accent-2", "bg", 4.5),
    ("成功色 / 页面底色", "success", "bg", 4.5),
    ("警告色 / 页面底色", "warn", "bg", 4.5),
    ("危险色 / 页面底色", "danger", "bg", 4.5),
    ("主按钮文字 / 主按钮底色", "accent-contrast", "accent", 4.5),
    ("危险按钮文字 / 危险按钮底色", "text-inverse", "danger", 4.5),
    ("控件边界 / 页面底色", "border-strong", "bg", 3.0),
    ("控件边界 / 卡片底色", "border-strong", "card-bg", 3.0),
    ("焦点环 / 页面底色", "focus-ring", "bg", 3.0),
    ("状态点 警告 / 徽章底色", "warn", "surface-2", 3.0),
    ("状态点 成功 / 徽章底色", "success", "surface-2", 3.0),
    ("状态点 危险 / 徽章底色", "danger", "surface-2", 3.0),
    ("主数字渐变起点 / 卡片底色", "accent", "card-bg", 3.0),
    ("主数字渐变终点 / 卡片底色", "accent-2", "card-bg", 3.0),
]

# (说明, 前景 token, 半透明底色 token, 压在哪一层 token 上, 最低比值)
# 浅色底是 rgba，必须按压底合成后的颜色算，否则会得出偏乐观的结果
TINTS = [
    ("警告文字 / 警告浅底(在卡片上)", "warn", "warn-subtle", "card-bg", 4.5),
    ("成功文字 / 成功浅底(在卡片上)", "success", "success-subtle", "card-bg", 4.5),
    ("危险文字 / 危险浅底(在卡片上)", "danger", "danger-subtle", "card-bg", 4.5),
    ("警告文字 / 警告浅底(在侧栏上)", "warn", "warn-subtle", "surface", 4.5),
    ("危险文字 / 危险浅底(在侧栏上)", "danger", "danger-subtle", "surface", 4.5),
    ("危险文字 / 危险浅底(在页面上)", "danger", "danger-subtle", "bg", 4.5),
]


def extract_block(text, marker):
    """取出 marker 选择器对应的那个 { ... } 块。

    必须按块取：文件里 :root 与 [data-theme="light"] 会出现同名令牌，
    如果整篇正则抓取，后面的浅色值会覆盖前面深色的值，校验的就不是默认主题了。

    匹配时要求标记后面紧跟 {，否则会命中注释里提到的同名文字
    （技能文件第 10 行注释里就写了 [data-theme="light"]）。
    """
    match = re.search(re.escape(marker) + r"\s*\{", text)
    if not match:
        raise ValueError("找不到选择器: %s" % marker)

    brace = text.index("{", match.start())
    depth = 0
    for index in range(brace, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[brace + 1 : index]
    raise ValueError("括号不配对: %s" % marker)


def parse_tokens(path, marker=":root"):
    """按 CSS 的层叠顺序解析令牌。

    主题块通常只覆写语义层，原始值仍来自 :root，所以要先铺 :root 再用主题块覆盖，
    否则 var() 解析不到底层值。
    """
    text = pathlib.Path(path).read_text(encoding="utf-8")

    tokens = {}
    if marker != ":root":
        tokens.update(
            re.findall(r"--([\w-]+)\s*:\s*([^;]+);", extract_block(text, ":root"))
        )

    tokens.update(re.findall(r"--([\w-]+)\s*:\s*([^;]+);", extract_block(text, marker)))
    return dict(tokens)


def resolve(name, tokens, depth=0):
    if depth > 12:
        raise ValueError("循环引用: --%s" % name)
    if name not in tokens:
        raise KeyError("没有这个令牌: --%s" % name)
    value = tokens[name].strip()
    match = re.fullmatch(r"var\(--([\w-]+)\)", value)
    if match:
        return resolve(match.group(1), tokens, depth + 1)
    return value


def to_rgba(value):
    """解析 #rgb / #rrggbb / rgb() / rgba()，返回归一化到 0~1 的四元组。"""
    value = value.strip()

    rgba = re.fullmatch(
        r"rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*(?:,\s*([\d.]+)\s*)?\)",
        value,
    )
    if rgba:
        r, g, b = (float(rgba.group(i)) / 255 for i in (1, 2, 3))
        alpha = float(rgba.group(4)) if rgba.group(4) is not None else 1.0
        return r, g, b, alpha

    v = value.lstrip("#")
    if len(v) == 3:
        v = "".join(c * 2 for c in v)
    return (*(int(v[i : i + 2], 16) / 255 for i in (0, 2, 4)), 1.0)


def to_rgb(value):
    return to_rgba(value)[:3]


def composite_over(foreground, base):
    """把带透明度的前景压在不透明底色上，得到实际显示出来的颜色。"""
    fr, fg, fb, alpha = to_rgba(foreground)
    br, bg, bb = to_rgb(base)
    return (
        fr * alpha + br * (1 - alpha),
        fg * alpha + bg * (1 - alpha),
        fb * alpha + bb * (1 - alpha),
    )


def luminance(rgb):
    def channel(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (channel(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_rgb(rgb1, rgb2):
    l1, l2 = luminance(rgb1), luminance(rgb2)
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def contrast(fg, bg):
    return contrast_rgb(to_rgb(fg), to_rgb(bg))


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "static/css/tokens.css"
    marker = sys.argv[2] if len(sys.argv) > 2 else ":root"
    tokens = parse_tokens(path, marker)

    print("检查 %s  区块 %s\n" % (path, marker))
    print("%-32s %-16s %-16s %8s %8s  %s"
          % ("检查项", "前景", "背景", "比值", "要求", "结果"))

    failures = []

    def report(label, fg_value, bg_value, ratio, minimum):
        passed = ratio >= minimum
        if not passed:
            failures.append((label, ratio, minimum))
        print("%-32s %-16s %-16s %8.2f %8.1f  %s"
              % (label, fg_value, bg_value, ratio, minimum,
                 "通过" if passed else "不达标"))

    for label, fg_name, bg_name, minimum in CHECKS:
        fg_value = resolve(fg_name, tokens)
        bg_value = resolve(bg_name, tokens)
        report(label, fg_value, bg_value, contrast(fg_value, bg_value), minimum)

    print()
    print("半透明浅底按合成后的颜色计算：")
    print()

    for label, fg_name, tint_name, base_name, minimum in TINTS:
        fg_value = resolve(fg_name, tokens)
        tint_value = resolve(tint_name, tokens)
        base_value = resolve(base_name, tokens)
        ratio = contrast_rgb(to_rgb(fg_value), composite_over(tint_value, base_value))
        report(label, fg_value, "%s over %s" % (tint_name, base_name), ratio, minimum)

    total = len(CHECKS) + len(TINTS)
    print()
    if failures:
        print("有 %d/%d 项不达标：" % (len(failures), total))
        for label, ratio, minimum in failures:
            print("  - %s：%.2f:1，要求 %.1f:1" % (label, ratio, minimum))
        return 1

    print("全部 %d 项达标。" % total)
    return 0


if __name__ == "__main__":
    sys.exit(main())
