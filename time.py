import requests
import logging
from datetime import datetime
import json
import os
import pytz
import pandas as pd
import time
import tkinter as tk
from tkinter import ttk

# إعداد سجل الأحداث
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# تحديد المنطقة الزمنية للسودان
sudan_timezone = pytz.timezone('Africa/Khartoum')

LOG_FILE = "advertisers_log.json"

def json_to_excel(json_file, excel_file):
    """ دالة لتحويل بيانات ملف JSON إلى ملف Excel """
    try:
        # فتح ملف JSON وقراءة البيانات
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # التأكد من أن البيانات ليست فارغة
        if not data:
            print("البيانات فارغة ولا يمكن تحويلها إلى Excel.")
            return

        # تحويل البيانات إلى DataFrame
        df = pd.DataFrame(data)

        # حفظ البيانات في ملف Excel
        df.to_excel(excel_file, index=False)

        print(f"تم تحويل البيانات إلى ملف Excel بنجاح! الملف تم حفظه هنا: {excel_file}")

    except FileNotFoundError:
        print(f"ملف JSON '{json_file}' غير موجود.")
    except json.JSONDecodeError:
        print("حدث خطأ أثناء قراءة ملف JSON. تأكد من أنه بصيغة صحيحة.")
    except Exception as e:
        print(f"حدث خطأ غير متوقع: {e}")

def fetch_binance_p2p_data(asset, fiat, trade_type, rows=20):
    """ جلب البيانات من Binance P2P API """
    url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"

    payload = {
        "asset": asset,
        "fiat": fiat,
        "merchantCheck": False,
        "page": 1,
        "rows": rows,
        "tradeType": trade_type
    }

    headers = {
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0"
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()
        return result.get("data", [])
    except requests.RequestException as e:
        logger.error(f"خطأ في جلب البيانات: {e}")
        return []

def filter_offers(offers):
    """ تصفية العروض بناءً على شرط أن يكون المعلن تاجرًا أو كمية التداول > 1000 """
    filtered_offers = []
    for offer in offers:
        advertiser = offer.get("advertiser", {})
        adv_details = offer.get("adv", {})

        is_merchant = advertiser.get("userType") == "merchant"
        tradable_quantity = float(adv_details.get("tradableQuantity", 0))

        if is_merchant or tradable_quantity > 1000:
            filtered_offers.append(offer)

    return filtered_offers

def calculate_average_price(offers):
    """ حساب متوسط السعر من العروض المصفاة """
    if not offers:
        return 0
    return sum(float(offer["adv"]["price"]) for offer in offers) / len(offers)

def fetch_latest_binance_data(asset="USDT", fiat="SDG"):
    """ جلب ومعالجة أحدث بيانات Binance P2P """
    # جلب البيانات وتصفيتها
    buy_offers = filter_offers(fetch_binance_p2p_data(asset, fiat, "BUY"))
    sell_offers = filter_offers(fetch_binance_p2p_data(asset, fiat, "SELL"))

    # حساب متوسط الأسعار
    avg_buy_price = calculate_average_price(buy_offers)
    avg_sell_price = calculate_average_price(sell_offers)

    # الحصول على الطابع الزمني الحالي
    timestamp = datetime.now(sudan_timezone).strftime("%Y-%m-%d %H:%M:%S")

    return {
               "timestamp": timestamp,
               "buy_price": avg_buy_price,
               "sell_price": avg_sell_price,
               "spread": avg_sell_price - avg_buy_price
           }, buy_offers, sell_offers

def save_price_data(data, filename="price_history.json"):
    """ حفظ بيانات الأسعار في ملف JSON """
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            history = json.load(f)
    else:
        history = []

    history.append(data)

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=4)

    logger.info(f"تم حفظ بيانات الأسعار في {filename}")

def save_advertisers_data(buy_offers, sell_offers, filename="advertisers_log.json"):
    """ حفظ بيانات المعلنين في ملف JSON """
    advertisers_data = []
    timestamp = datetime.now(sudan_timezone).strftime("%Y-%m-%d %H:%M:%S")

    for offer in buy_offers + sell_offers:
        advertiser = offer.get("advertiser", {})
        adv_details = offer.get("adv", {})

        advertiser_entry = {
            "timestamp": timestamp,
            "name": advertiser.get("nickName", "غير معروف"),
            "trade_type": "BUY" if offer in buy_offers else "SELL",
            "price": float(adv_details.get("price", 0)),
            "quantity": float(adv_details.get("tradableQuantity", 0)),
            "is_merchant": advertiser.get("userType") == "merchant"
        }
        advertisers_data.append(advertiser_entry)

    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)
    else:
        existing_data = []

    existing_data.extend(advertisers_data)

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(existing_data, f, ensure_ascii=False, indent=4)

    logger.info(f"تم حفظ بيانات المعلنين في {filename}")

def load_data():
    """ تحميل بيانات المعلنين من ملف JSON """
    try:
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def create_gui():
    """ إنشاء واجهة المستخدم باستخدام Tkinter """
    root = tk.Tk()
    root.title("📌 سجل المعلنين")
    root.geometry("700x400")

    # إنشاء جدول
    columns = ("التاريخ", "اسم المعلن", "نوع العرض", "السعر", "الكمية", "تاجر؟")
    tree = ttk.Treeview(root, columns=columns, show="headings")

    # تعيين عناوين الأعمدة
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, anchor="center")

    # تحميل البيانات وإضافتها للجدول
    advertisers = load_data()
    for ad in advertisers:
        trade_type = "شراء" if ad["trade_type"] == "BUY" else "بيع"
        is_merchant = "نعم" if ad["is_merchant"] else "لا"
        tree.insert("", "end", values=(ad["timestamp"], ad["name"], trade_type, ad["price"], ad["quantity"], is_merchant))

    # إضافة الجدول إلى النافذة
    tree.pack(expand=True, fill="both")

    # تشغيل الواجهة
    root.mainloop()

def main():
    """ الدالة الرئيسية لتحديث البيانات """
    price_data, buy_offers, sell_offers = fetch_latest_binance_data(asset="USDT", fiat="SDG")

    # حفظ البيانات
    save_price_data(price_data)
    save_advertisers_data(buy_offers, sell_offers)

    # عرض البيانات
    print("\n📌 **تم تحديث البيانات**")
    print(json.dumps(price_data, indent=4, ensure_ascii=False))

# تشغيل الدالة مرة واحدة فقط


    # تحويل ملفات JSON إلى Excel بعد تنفيذ التحديث مرة واحدة
    json_to_excel("price_history.json", "price_history.xlsx")
    json_to_excel("advertisers_log.json", "advertisers_log.xlsx")
if __name__ == '__main__':
    main()
