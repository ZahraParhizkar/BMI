# app.py
import streamlit as st
from datetime import datetime
import textwrap
import io
st.image("logo-removebg-preview.png", use_column_width=True)
# -------------------- راست‌چین کردن متن‌ها --------------------
st.markdown("""
    <style>
    body, .stApp {
        direction: rtl;
        text-align: right;
    }
    </style>
""", unsafe_allow_html=True)

st.set_page_config(page_title="ارزیابی BMI و توصیه‌های لازم", layout="centered")

# ---------- helper functions ----------
def calc_bmi(weight_kg, height_cm):
    h_m = height_cm / 100.0
    if h_m <= 0:
        return None
    bmi = weight_kg / (h_m * h_m)
    return round(bmi, 2)

def classify_bmi(bmi, ethnicity):
    """
    Returns (label, class_number) based on NIH/WHO with Asian adjustment.
    For Asian: overweight >=23, obesity >=25 (per provided text).
    """
    if bmi is None:
        return ("نامشخص", None)
    if ethnicity == "Asian":
        if bmi < 23:
            return ("وزن طبیعی", 0)
        if 23 <= bmi < 25:
            return ("اضافه وزن (آسیایی)", 1)
        if 25 <= bmi < 30:
            return ("چاقی (Class I-II) — آسیایی", 2)
        if bmi >= 30:
            return ("چاقی شدید (Class III) — آسیایی", 3)
    else:
        if bmi < 18.5:
            return ("کم‌وزنی", -1)
        if 18.5 <= bmi < 25:
            return ("وزن طبیعی", 0)
        if 25 <= bmi < 30:
            return ("اضافه وزن", 1)
        if 30 <= bmi < 35:
            return ("چاقی (Class I)", 2)
        if 35 <= bmi < 40:
            return ("چاقی (Class II)", 3)
        if bmi >= 40:
            return ("چاقی شدید (Class III)", 4)

def waist_thresholds(sex, ethnicity):
    """
    returns (threshold_cm, label)
    Non-Asian: male >=102 cm, female >=88 cm
    Asian: male >=90 cm, female >=80 cm
    These numbers are taken from the provided text.
    """
    if ethnicity == "Asian":
        if sex == "مذکر":
            return (90, "افزایش ریسک (آسیایی - مرد)")  # 90 cm
        else:
            return (80, "افزایش ریسک (آسیایی - زن)")   # 80 cm
    else:
        if sex == "مذکر":
            return (102, "افزایش ریسک (غیرآسیایی - مرد)")  # 102 cm
        else:
            return (88, "افزایش ریسک (غیرآسیایی - زن)")   # 88 cm

def waist_to_height_ratio(waist_cm, height_cm):
    if height_cm <= 0:
        return None
    return round(waist_cm / height_cm, 2)

def waist_to_hip_ratio(waist_cm, hip_cm):
    if hip_cm == 0:
        return None
    return round(waist_cm / hip_cm, 2)

def determine_risk_category(bmi, has_abdominal_obesity, comorbidities_present):
    """
    Using the framework in the text:
    - Low risk: BMI 25-29.9 without abdominal obesity and without obesity-related diseases
    - Moderate risk: BMI 25-29.9 with abdominal obesity or BMI >=30 without abdominal obesity
    - High risk: BMI >=30 with abdominal adiposity or presence of weight-related diseases
    We'll also consider BMI <25 as low risk (usually prevention).
    """
    if bmi is None:
        return "نامشخص"
    if bmi < 25:
        return "پایین (پیشنهاد: پیشگیری از افزایش وزن)"
    if 25 <= bmi < 30:
        if has_abdominal_obesity or comorbidities_present:
            return "متوسط (مشاوره برای کاهش وزن — ممکن است دارو/ارجاع لازم باشد)"
        else:
            return "پایین‌-متوسط (پیشنهاد: پیشگیری از افزایش وزن و تغییر سبک زندگی)"
    # bmi >= 30
    if bmi >= 30:
        if has_abdominal_obesity or comorbidities_present:
            return "بالا (مدیریت فشرده — رژیم، فعالیت، دارو، و احتمالاً جراحی)"
        else:
            return "متوسط-تا-بالا (پیشنهاد: مدیریت فعال وزن، بررسی عوامل خطر)"
    return "نامشخص"

def generate_recommendations(bmi, bmi_label, sex, ethnicity, waist_cm, wthr, whr, comorbidities, meds_cause_weight, age):
    recs = []
    # BMI specific
    if bmi is None:
        recs.append("۳) BMI نامشخص است — ورودی‌ها را بررسی کنید.")
    else:
        if bmi < 25:
            recs.append("• وضعیت: BMI در محدودهٔ طبیعی یا کم‌وزنی. توصیه: پیشگیری از افزایش وزن؛ توجه به تغذیه متعادل و فعالیت بدنی منظم.")
        elif 25 <= bmi < 30:
            if ethnicity == "Asian":
                recs.append("• توجه: برای افراد آسیایی آستانه‌ها پایین‌تر است؛ BMI در این محدوده ممکن است معنی‌دارتر برای ریسک متابولیک باشد.")
            recs.append("• وضعیت: اضافه وزن. توصیه: مشاوره تغذیه و فعالیت؛ اگر دورکمر بالاست یا بیماری‌های مرتبط هست، بررسی بیشتر و درمان هدفمند مورد نیاز است.")
        else:  # bmi >=30
            recs.append("• وضعیت: چاقی (BMI ≥ 30). توصیه: مدیریت فعال شامل تغییر سبک زندگی، مداخلات رفتاری، بررسی گزینهٔ دارویی ضدچاقی و ارزیابی برای گزینه‌های جراحی (در موارد مناسب).")

    # abdominal obesity
    thr, thr_label = waist_thresholds(sex, ethnicity)
    if waist_cm is not None:
        if waist_cm >= thr:
            recs.append(f"۳) دور کمر: مقدار {waist_cm} cm بالاتر از آستانهٔ پیشنهادی ({thr} cm) برای گروه شماست — نشان‌دهندهٔ افزایش خطر متابولیک.")
        else:
            recs.append(f"۳) دور کمر: مقدار {waist_cm} cm کمتر از آستانهٔ {thr} cm است.")
    if wthr is not None:
        if wthr > 0.5:
            recs.append(f"۴) نسبت دورکمر:قد/کمر = {wthr} (>0.5) — این نشان‌دهندهٔ چاقی مرکزی و افزایش خطر است.")
        else:
            recs.append(f"۴) نسبت دورکمر:قد/کمر = {wthr} (≤0.5) — نسبت مرکزی طبیعی‌تر است.")

    if whr is not None:
        if (sex == "مذکر" and whr >= 0.90) or (sex == "مونث" and whr >= 0.85) or (sex == "زن" and whr >= 0.85):
            recs.append(f"۵) نسبت کمر-باسن = {whr} — در محدوده‌ای که ریسک متابولیک افزایش می‌یابد.")
        else:
            recs.append(f"۵) نسبت کمر-باسن = {whr} — در محدودهٔ کمتر از آستانهٔ عمومی.")

    # labs recommendation
    if bmi >= 25 or (waist_cm is not None and waist_cm >= thr):
        recs.append("۶) آزمایش‌های اولیه پیشنهاد شده: قند ناشتا یا HbA1c، TSH، آنزیم‌های کبدی (ALT/AST)، چربی‌های خون (فاستینگ لیپیدها).")
    else:
        recs.append("۶) در فرد با ریسک کم، آزمایش‌های پایه بر اساس سابقهٔ فردی و بالینی تصمیم‌گیری شود.")

    # comorbidities and meds
    if comorbidities:
        recs.append(f"۷) بیماری‌های همراه گزارش شده: {', '.join(comorbidities)} — اینها میزان ریسک را افزایش می‌دهند و باید همزمان مدیریت شوند.")
    if meds_cause_weight:
        recs.append("۸) داروهایی که می‌توانند باعث افزایش وزن شوند باید بازنگری شوند (مثال‌ها: انسولین، سولفونیل‌ها، گلوتازون‌ها، گلوکوکورتیکوئیدها، برخی آنتی‌سایکوتیک‌ها). در صورت امکان با پزشک تجویزکننده بررسی کنید.")
    # referrals and intensive management
    risk_cat = determine_risk_category(bmi, (waist_cm is not None and waist_cm >= thr), len(comorbidities) > 0)
    if "بالا" in risk_cat or "شدید" in risk_cat or bmi >= 35:
        recs.append("۹) توصیهٔ ارجاع: بررسی گزینه‌های مدیریت فشرده — ارجاع به تغذیه‌شناس بالینی، کلینیک چاقی یا جراح متابولیک (در موارد مناسب). بحث دربارهٔ درمان دارویی یا جراحی در صورت اندیکاسیون.")
    elif "متوسط" in risk_cat:
        recs.append("۹) برای گروه متوسط: برنامهٔ کاهش وزن ساختاریافته با پیگیری منظم؛ ممکن است دارو یا ارجاع به برنامه‌های تخصصی مناسب باشد.")
    else:
        recs.append("۹) برای گروه با ریسک کمتر: پیگیری و پیشگیری از افزایش وزن؛ آموزش سبک زندگی.")

    # age considerations
    if age >= 60:
        recs.append("۱۰) افراد بالای 60 سال: BMI ممکن است کمتر منعکس‌کنندهٔ چربی واقعی باشد (کاهش تودهٔ عضلانی). اندازه‌گیری دورکمر و ارزیابی عملکردی مهم است.")
    # closing
    recs.append("۱۱) نکتهٔ مهم: این خروجی راهنماست و جایگزین مشاورهٔ پزشکی حضوری نیست. در صورت وجود نگرانی‌ها یا بیماری‌های زمینه‌ای با پزشک معالج مشورت کنید.")
    return recs

def format_report(name, inputs, results, recommendations):
    header = f"گزارش ارزیابی وزن — تولید شده در {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    if name:
        header = f"نام: {name}\n" + header
    body = []
    body.append("=== ورودی‌ها ===")
    for k,v in inputs.items():
        body.append(f"{k}: {v}")
    body.append("\n=== نتایج محاسبات ===")
    for k,v in results.items():
        body.append(f"{k}: {v}")
    body.append("\n=== توصیه‌ها ===")
    for i, r in enumerate(recommendations, 1):
        body.append(f"{i}. {r}")
    return "\n".join(body)

# ---------- App UI ----------
st.title("ارزیابی BMI و توصیه‌های لازم")
st.markdown(
    """
    این برنامه با استفاده از پارامترهایی که وارد می‌کنید، BMI و معیارهای مرکزی (دور کمر، نسبت‌ها) را محاسبه می‌کند و بر اساس دستورالعمل‌ها و آستانه‌های ذکر شده در آپتودیت توصیه‌هایی ارائه می‌دهد.
    **توجه**: این ابزار تنها جنبهٔ آموزشی/راهنمایی دارد و جایگزین معاینه و مشاورهٔ پزشکی تخصصی نیست.
    """
)

with st.form("input_form"):
    st.subheader("ورودی‌های فردی")
    name = st.text_input("نام (اختیاری)")
    col1, col2, col3 = st.columns(3)
    with col1:
        age = st.number_input("سن (سال)", min_value=0, max_value=120, value=35)
        sex = st.selectbox("جنسیت", options=["مونث", "مذکر", "سایر/ترجیح به ذکر نشده"])
    with col2:
        weight = st.number_input("وزن (کیلوگرم)", min_value=1.0, max_value=500.0, value=70.0, format="%.1f")
        height_cm = st.number_input("قد (سانتی‌متر)", min_value=30.0, max_value=300.0, value=170.0, format="%.1f")
    with col3:
        waist_cm = st.number_input("دور کمر (سانتی‌متر) — اگر اندازه ندارید بگذارید 0", min_value=0.0, max_value=300.0, value=85.0, format="%.1f")
        hip_cm = st.number_input("دور باسن (سانتی‌متر) — اگر ندارید 0", min_value=0.0, max_value=300.0, value=100.0, format="%.1f")
    ethnicity = st.selectbox("نژاد/گروه جمعیتی (برای تنظیم آستانه‌ها)", options=["White/Hispanic/Black/Other", "Asian"])
    st.subheader("سابقه پزشکی و دارویی")
    com1 = st.checkbox("دیابت نوع 2 (یا قند بالا/پیش‌دیابت)")
    com2 = st.checkbox("فشارخون بالا")
    com3 = st.checkbox("دیس‌لیپیدمی (چربی خون غیرطبیعی)")
    com4 = st.checkbox("آپنهٔ انسدادی خواب")
    com5 = st.checkbox("بیماری قلبی عروقی (CHD)")
    com6 = st.checkbox("کبد چرب یا آنزیم‌های کبدی بالا")
    com7 = st.checkbox("آرتروز علامت‌دار")
    other_com = st.text_input("سایر بیماری‌ها (کامای جداکننده) — اختیاری")
    meds_cause_weight = st.multiselect(
        "آیا از داروهای شناخته‌شده باعث افزایش وزن استفاده می‌کنید؟ (انتخاب کنید)",
        options=[
            "انسولین",
            "سولفونیلورها",
            "تيازوليدينديون‌ها (مثلاً Pioglitazone)",
            "گلوکوکورتیکوئیدها",
            "برخی آنتی‌سایکوتیک‌ها",
            "هیچکدام/نمی‌دانم"
        ],
        default=[]
    )
    submit = st.form_submit_button("محاسبه و تولید توصیه")

if submit:
    # gather inputs
    comorbidities = []
    for flag, label in [(com1, "دیابت/پیش‌دیابت"), (com2, "فشارخون بالا"), (com3, "دیس‌لیپیدمی"), (com4, "آپنهٔ خواب"), (com5, "بیماری قلبی"), (com6, "کبد چرب/آنزیم بالا"), (com7, "آرتروز")]:
        if flag:
            comorbidities.append(label)
    if other_com.strip():
        other_items = [p.strip() for p in other_com.split(",") if p.strip()]
        comorbidities.extend(other_items)

    if "هیچکدام/نمی‌دانم" in meds_cause_weight and len(meds_cause_weight) > 1:
        # remove other selections if "هیچکدام/نمی‌دانم" present
        meds_list = ["هیچکدام/نمی‌دانم"]
    else:
        meds_list = meds_cause_weight

    bmi = calc_bmi(weight, height_cm)
    bmi_label = classify_bmi(bmi, "Asian" if ethnicity == "Asian" else "Other")[0]
    wthr = waist_to_height_ratio(waist_cm if waist_cm>0 else None, height_cm) if waist_cm>0 else None
    whr = waist_to_hip_ratio(waist_cm if waist_cm>0 else None, hip_cm if hip_cm>0 else None) if (waist_cm>0 and hip_cm>0) else None
    thr, thr_label = waist_thresholds(sex, "Asian" if ethnicity == "Asian" else "Other")
    has_abdominal = (waist_cm is not None and waist_cm >= thr) if waist_cm>0 else False

    risk_cat = determine_risk_category(bmi, has_abdominal, len(comorbidities)>0)

    recommendations = generate_recommendations(bmi, bmi_label, sex, "Asian" if ethnicity=="Asian" else "Other", waist_cm if waist_cm>0 else None, wthr, whr, comorbidities, meds_list, age)

    # display results
    st.subheader("نتایج کلی")
    colA, colB = st.columns(2)
    with colA:
        st.metric("BMI", f"{bmi if bmi is not None else 'نامشخص'}")
        st.write("طبقه‌بندی BMI:")
        st.info(bmi_label)
    with colB:
        st.write("ریسک کلی (بر اساس BMI، چاقی مرکزی و بیماری‌های همراه):")
        if "بالا" in risk_cat:
            st.error(risk_cat)
        elif "متوسط" in risk_cat:
            st.warning(risk_cat)
        else:
            st.success(risk_cat)

    st.markdown("---")
    st.subheader("معیارهای مرکزی")
    st.write(f"- دور کمر: {waist_cm if waist_cm>0 else 'وارد نشده'} cm (آستانهٔ مرجع برای شما: {thr} cm)")
    st.write(f"- نسبت دورکمر/قد: {wthr if wthr is not None else 'نامشخص'} (نشان‌دهندهٔ ریسک مرکزی: >0.5)")
    st.write(f"- نسبت کمر/باسن: {whr if whr is not None else 'نامشخص'} (آستانه‌ها: مرد ≥0.90، زن ≥0.85)")

    st.markdown("---")
    st.subheader("آزمایش‌ها و ارزیابی‌های پیشنهادی")
    if bmi is None:
        st.write("BMI محاسبه نشد — ورودی‌ها را بررسی کنید.")
    else:
        if bmi >= 25 or (waist_cm>0 and waist_cm >= thr):
            st.write("- آزمایش‌های پایه پیشنهاد شده:")
            st.write("  * قند ناشتا و/یا HbA1c")
            st.write("  * TSH")
            st.write("  * آنزیم‌های کبدی (ALT, AST)")
            st.write("  * لیپیدها (فاستینگ لیپید پنل)")
        else:
            st.write("- براساس وضعیت فعلی، ممکن است نیاز به آزمایش پایه براساس تاریخچهٔ بالینی باشد.")

    st.markdown("---")
    st.subheader("توصیه‌های کاربردی (خلاصه)")
    for r in recommendations:
        st.write("- " + r)

    st.markdown("---")
    st.subheader("گزارش قابل دانلود")
    inputs = {
        "وزن (kg)": weight,
        "قد (cm)": height_cm,
        "سن": age,
        "جنسیت": sex,
        "نژاد/گروه": ethnicity,
        "دور کمر (cm)": waist_cm,
        "دور باسن (cm)": hip_cm,
        "بیماری‌های همراه": ", ".join(comorbidities) if comorbidities else "ندارد",
        "داروهای موثر بر وزن": ", ".join(meds_list) if meds_list else "ندارد"
    }
    results = {
        "BMI": bmi,
        "طبقه‌بندی BMI": bmi_label,
        "نسبت دورکمر/قد": wthr,
        "نسبت کمر/باسن": whr,
        "آستانهٔ دورکمر (برای شما)": f"{thr} cm",
        "دستهٔ ریسک کلی": risk_cat
    }
    report_text = format_report(name, inputs, results, recommendations)
    st.text_area("گزارش (متن)", value=report_text, height=300)
    # download
    b = report_text.encode("utf-8")
    st.download_button("دانلود گزارش (TXT)", data=b, file_name="obesity_report.txt", mime="text/plain")

st.markdown("---")
st.caption("منبع: UpToDate")
