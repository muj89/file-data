import json
from datetime import datetime

# الحصول على الوقت والتاريخ الحالي
current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

# البيانات التي سيتم تخزينها في ملف JSON
data = {
    "message": "Hello from Python!",
    "status": "success",
    "items": [1, 2, 3],
    "timestamp": current_time  # إضافة الوقت والتاريخ الحالي
}

# كتابة البيانات في ملف JSON
with open("data.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=4, ensure_ascii=False)

# طباعة رسالة عند إنشاء الملف
print("data.json created with timestamp.")
