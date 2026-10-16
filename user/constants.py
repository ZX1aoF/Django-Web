"""user 应用中共用的常量。"""

# 账号 = 年级(4 位) + 序号(6 位)，共 10 位
GRADE_LENGTH = 4
NUMBER_LENGTH = 6
UID_LENGTH = GRADE_LENGTH + NUMBER_LENGTH

# 身份标识，与 URL 里的 <slug:kind> 取值保持一致
KIND_STUDENT = "student"
KIND_ADMINISTRATOR = "administrator"
KINDS = (KIND_STUDENT, KIND_ADMINISTRATOR)

# kind 参数非法时返回的提示
INVALID_KIND = "身份参数无效：kind 只能是 student 或 administrator。"
