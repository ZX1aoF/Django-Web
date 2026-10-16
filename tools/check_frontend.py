"""前端自检：CSS 规则 + 实际渲染出的 HTML 结构。

对应 website-ui-designer 技能 Stage 5 自检清单里**可以程序化验证**的部分：

  CSS
    - 媒体查询一律 min-width（移动优先）
    - 容器不写死像素宽度
    - 表格有横向滚动兜底、弹性子项有 min-width: 0
    - 有 prefers-reduced-motion 兜底、用了 100dvh
    - app.css 里不出现裸色值（必须走令牌）

  HTML
    - 每页恰好一个 h1
    - 每个 label[for] 都能找到对应 id 的控件
    - 没有行内 style
    - 没有 lorem 占位文案
    - 有跳过导航链接与带 aria-label 的 nav

**无法程序化验证**的部分（真实视觉观感、各断点下是否重叠），本脚本不覆盖，
需要在浏览器里逐档人工核对。

用法：
    python check_frontend.py <project_dir> <页面目录>

<页面目录> 里放的是已经抓下来的 .html 文件。
"""

import pathlib
import re
import sys
from html.parser import HTMLParser


class StructureProbe(HTMLParser):
    """统计 h1 数量、label/for 配对、行内 style 等结构特征。"""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.h1_count = 0
        self.ids = set()
        self.label_fors = []
        self.inline_styles = 0
        self.navs = []
        self.has_skip_link = False
        self.images_without_alt = 0

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if "id" in attributes:
            self.ids.add(attributes["id"])
        if "style" in attributes:
            self.inline_styles += 1
        if tag == "h1":
            self.h1_count += 1
        if tag == "label" and "for" in attributes:
            self.label_fors.append(attributes["for"])
        if tag == "nav":
            self.navs.append(attributes.get("aria-label"))
        if tag == "a" and attributes.get("href") == "#main":
            self.has_skip_link = True
        if tag == "img" and "alt" not in attributes:
            self.images_without_alt += 1


def check_css(root):
    app_css = (root / "static/css/app.css").read_text(encoding="utf-8")
    tokens_css = (root / "static/css/tokens.css").read_text(encoding="utf-8")

    results = []

    def add(name, ok, detail=""):
        results.append((name, ok, detail))

    # 只看断点类媒体查询；prefers-reduced-motion 这类不是断点，不该参与判断
    breakpoints = [q.strip() for q in re.findall(r"@media[^{]+", app_css) if "width" in q]
    not_mobile_first = [q for q in breakpoints if "min-width" not in q]
    add("app.css 断点全部移动优先(min-width)", not not_mobile_first,
        "；".join(not_mobile_first))

    raw_hex = re.findall(r"#[0-9a-fA-F]{3,8}\b", app_css)
    add("app.css 不出现裸色值", not raw_hex, "；".join(sorted(set(raw_hex))))

    # 只查「固定宽度的容器」：排除 max-/min-/border-*-width，且只有超过 200px 才算问题
    # （图标、圆点、发丝线用 px 是允许的）
    wide = [w for w in re.findall(r"(?<![\w-])width\s*:\s*(\d+)px", app_css) if int(w) > 200]
    add("app.css 没有固定宽度容器(>200px)", not wide, "；".join(wide))

    add("表格有横向滚动兜底", "overflow-x: auto" in app_css)
    add("弹性子项有 min-width: 0", "min-width: 0" in app_css)
    add("app.css 有减少动效兜底", "prefers-reduced-motion" in app_css)
    add("tokens.css 有减少动效兜底", "prefers-reduced-motion" in tokens_css)
    add("使用了 100dvh 而非 100vh", "100dvh" in app_css and "100vh" not in app_css)
    add("tokens.css 定义了 :focus-visible", ":focus-visible" in tokens_css)
    add("app.css 覆盖了三种状态徽章",
        all("pill--" + s in app_css for s in ("pending", "approved", "rejected")))

    return results


def check_pages(page_dir):
    results = []
    for path in sorted(page_dir.glob("*.html")):
        html = path.read_text(encoding="utf-8")
        probe = StructureProbe()
        probe.feed(html)

        name = path.stem

        def add(what, ok, detail=""):
            results.append(("%s · %s" % (name, what), ok, detail))

        add("恰好一个 h1", probe.h1_count == 1, "实际 %d 个" % probe.h1_count)

        dangling = [f for f in probe.label_fors if f not in probe.ids]
        add("label[for] 都有对应控件", not dangling, "；".join(dangling))

        add("没有行内 style", probe.inline_styles == 0, "%d 处" % probe.inline_styles)
        add("没有 lorem 占位", "lorem" not in html.lower())
        add("有跳过导航链接", probe.has_skip_link)
        # 没有 nav 的页面（登录/注册）不算问题；有 nav 就必须带 aria-label
        add("nav 元素都带 aria-label", all(probe.navs))
        add("图片都有 alt", probe.images_without_alt == 0,
            "%d 张缺 alt" % probe.images_without_alt)

        # 状态不能只靠颜色：徽章里必须同时有文字（跨行匹配）
        if "pill--" in html:
            add("状态徽章同时带文字",
                bool(re.search(r'pill--\w+[^>]*>.*?[\u4e00-\u9fa5]+', html, re.DOTALL)))

    return results


def main():
    root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    page_dir = pathlib.Path(sys.argv[2] if len(sys.argv) > 2 else "pages")

    results = check_css(root) + check_pages(page_dir)

    width = max(len(name) for name, _, _ in results)
    failures = 0
    for name, ok, detail in results:
        if not ok:
            failures += 1
        print("%-*s  %s%s" % (width, name, "通过" if ok else "不通过",
                              ("   " + detail) if detail and not ok else ""))

    print()
    if failures:
        print("%d/%d 项不通过。" % (failures, len(results)))
        return 1
    print("全部 %d 项通过。" % len(results))
    return 0


if __name__ == "__main__":
    sys.exit(main())
