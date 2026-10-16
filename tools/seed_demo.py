"""往本地开发库里放一批演示素材。

目的：列表页只有两三条数据时，看不出密度、分页与筛选的真实效果。
这些素材全部归入预置的「诗词」分类，所以用 ?category=<诗词> 就能一次看到
分页 + 筛选标签 + 分面计数。

用法（在项目根目录，用项目自己的虚拟环境）：
    python tools/seed_demo.py

幂等：按标题 get_or_create，重复执行不会重复插入。
"""

import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "SE.settings")
django.setup()

from material.models import Category, Material  # noqa: E402
from user.models import Administrator, Student  # noqa: E402

# (标题, 出处 / 作者, 正文)
DEMO = [
    ("静夜思", "李白《静夜思》", "床前明月光，疑是地上霜。\n举头望明月，低头思故乡。"),
    ("春晓", "孟浩然《春晓》", "春眠不觉晓，处处闻啼鸟。\n夜来风雨声，花落知多少。"),
    ("登鹳雀楼", "王之涣《登鹳雀楼》", "白日依山尽，黄河入海流。\n欲穷千里目，更上一层楼。"),
    ("江雪", "柳宗元《江雪》", "千山鸟飞绝，万径人踪灭。\n孤舟蓑笠翁，独钓寒江雪。"),
    ("相思", "王维《相思》", "红豆生南国，春来发几枝。\n愿君多采撷，此物最相思。"),
    ("陋室铭", "刘禹锡《陋室铭》", "山不在高，有仙则名。水不在深，有龙则灵。\n斯是陋室，惟吾德馨。"),
    ("爱莲说", "周敦颐《爱莲说》", "予独爱莲之出淤泥而不染，濯清涟而不妖。"),
    ("岳阳楼记（节选）", "范仲淹《岳阳楼记》", "先天下之忧而忧，后天下之乐而乐。"),
    ("兰亭集序（节选）", "王羲之《兰亭集序》", "此地有崇山峻岭，茂林修竹，又有清流激湍。"),
    ("劝学（节选）", "荀子《劝学》", "不积跬步，无以至千里；不积小流，无以成江海。"),
    ("师说（节选）", "韩愈《师说》", "师者，所以传道受业解惑也。"),
    ("荷塘月色（节选）", "朱自清《荷塘月色》", "曲曲折折的荷塘上面，弥望的是田田的叶子。"),
    ("背影（节选）", "朱自清《背影》", "我看见他戴着黑布小帽，穿着黑布大马褂，深青布棉袍。"),
    ("再别康桥（节选）", "徐志摩《再别康桥》", "悄悄的我走了，正如我悄悄的来；我挥一挥衣袖，不带走一片云彩。"),
    ("乡愁（节选）", "余光中《乡愁》", "乡愁是一枚小小的邮票，我在这头，母亲在那头。"),
    ("雨巷（节选）", "戴望舒《雨巷》", "撑着油纸伞，独自彷徨在悠长、悠长又寂寥的雨巷。"),
]

CATEGORY_NAME = "诗词"


def main():
    category = Category.objects.filter(name=CATEGORY_NAME).first()
    if category is None:
        raise SystemExit("找不到预置分类「%s」，请先执行 manage.py migrate" % CATEGORY_NAME)

    administrator = Administrator.objects.first()
    if administrator is None:
        raise SystemExit("库里没有管理员账号，请先注册一个管理员再跑这个脚本")

    student = Student.objects.first()

    created = 0
    for index, (title, source, body) in enumerate(DEMO):
        material, is_new = Material.objects.get_or_create(
            title=title,
            defaults={
                "category": category,
                "source": source,
                "body": body,
                "created_by": administrator,
                "status": Material.Status.APPROVED,
            },
        )
        if is_new:
            created += 1
        elif not material.category_id:
            material.category = category
            material.save(update_fields=["category"])

    # 留一条学生投稿，让审核队列不是空的
    if student is not None:
        Material.objects.get_or_create(
            title="天净沙·秋思",
            defaults={
                "category": category,
                "source": "马致远《天净沙·秋思》",
                "body": "枯藤老树昏鸦，小桥流水人家，古道西风瘦马。",
                "submitted_by": student,
                "status": Material.Status.PENDING,
            },
        )

    print("新增 %d 条，当前素材总数 %d 条" % (created, Material.objects.count()))
    print("  已通过 %d 条 / 待审核 %d 条"
          % (Material.objects.filter(status=Material.Status.APPROVED).count(),
             Material.objects.filter(status=Material.Status.PENDING).count()))
    print("  「%s」分类下 %d 条 —— 用它筛一下就够翻页了"
          % (CATEGORY_NAME, Material.objects.filter(category=category).count()))


if __name__ == "__main__":
    main()
