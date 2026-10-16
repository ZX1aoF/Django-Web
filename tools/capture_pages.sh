#!/usr/bin/env bash
# 抓取某一版的渲染结果，供并排对照使用。
#
# 用法：capture_pages.sh <base_url> <输出目录>
#   例：capture_pages.sh http://127.0.0.1:8003 /tmp/after
#
# 抓 7 个页面，覆盖两类身份与匿名态。需要该站点上存在下面的测试账号。

set -e

BASE="${1:?需要 base_url}"
OUT="${2:?需要输出目录}"
ADMIN_UID="${3:-2024000001}"
ADMIN_PASS="${4:-admin-strong-pass}"
STU_UID="${5:-2021000001}"
STU_PASS="${6:-123}"
MATERIAL_PK="${7:-2}"

rm -rf "$OUT"
mkdir -p "$OUT"

token() { grep csrftoken "$1" | awk '{print $7}' | tail -1; }

login() { # jar kind uid pass
  rm -f "$1"
  curl -s -c "$1" -o /dev/null "$BASE/user/login/$2"
  curl -s -b "$1" -c "$1" -o /dev/null -X POST \
    -d "csrfmiddlewaretoken=$(token "$1")&uid=$3&password=$4" "$BASE/user/login/$2"
}

login /tmp/cap-admin.jar administrator "$ADMIN_UID" "$ADMIN_PASS"
login /tmp/cap-stu.jar student "$STU_UID" "$STU_PASS"

# 匿名
curl -s -o "$OUT/1-index.html"    "$BASE/"
curl -s -o "$OUT/2-login.html"    "$BASE/user/login/student"
curl -s -o "$OUT/3-register.html" "$BASE/user/register/student"

# 管理员
curl -s -b /tmp/cap-admin.jar -o "$OUT/4-list.html"   "$BASE/material/administrator/"
curl -s -b /tmp/cap-admin.jar -o "$OUT/5-detail.html" "$BASE/material/administrator/detail/$MATERIAL_PK"
curl -s -b /tmp/cap-admin.jar -o "$OUT/6-review.html" "$BASE/material/administrator/review/$MATERIAL_PK"

# 学生
curl -s -b /tmp/cap-stu.jar   -o "$OUT/7-form.html"   "$BASE/material/student/create"

# 管理员，带筛选：用来展示结果计数、筛选标签与分页
# 演示数据脚本把 16 条素材放进了「诗词」分类（pk=1），够翻两页
curl -s -b /tmp/cap-admin.jar -o "$OUT/8-catalog.html" \
  "$BASE/material/administrator/?category=${CATEGORY_PK:-1}"

for file in "$OUT"/*.html; do
  printf "  %-20s %6s 字节\n" "$(basename "$file")" "$(wc -c < "$file")"
done
