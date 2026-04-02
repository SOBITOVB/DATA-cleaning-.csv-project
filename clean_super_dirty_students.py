import pandas as pd
import numpy as np
import re
import json
import ast

INPUT_FILE = "super_dirty_students.csv"
OUTPUT_FILE = "super_dirty_students_cleaned.csv"

word_num = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
    "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
    "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20, "thirty": 30,
    "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90
}

email_pattern = re.compile(r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')


def clean_text(x):
    if pd.isna(x):
        return np.nan
    if not isinstance(x, str):
        return x
    x = x.strip()
    if x == "":
        return np.nan
    if x.lower() in ["nan", "null", "none", "n/a", "na", "missing"]:
        return np.nan
    return x


def to_number(x):
    if pd.isna(x):
        return np.nan

    x = str(x).strip().lower()

    if x == "":
        return np.nan

    if x in word_num:
        return float(word_num[x])

    if x == "four point five":
        return 4.5

    m = re.search(r'[-+]?\d+(?:[.,]\d+)?', x)
    if m:
        return float(m.group(0).replace(",", "."))

    return np.nan


def clean_numeric(col, name):
    col = col.map(clean_text)

    if name == "money_spent":
        col = col.astype(str)
        col = col.str.replace(r"(?i)usd", "", regex=True)
        col = col.str.replace("$", "", regex=False)
        col = col.str.replace(",", ".", regex=False)
        col = col.str.replace(r"[^0-9.\-]", "", regex=True)
        col = pd.to_numeric(col, errors="coerce")
        col[col < 0] = np.nan
        return col.astype("Float64")

    nums = col.map(to_number)

    if name == "age":
        nums[(nums < 15) | (nums > 100)] = np.nan
        return nums.round().astype("Int64")

    if name == "score":
        nums[(nums < 0) | (nums > 100)] = np.nan
        return nums.round().astype("Int64")

    if name == "attendance":
        nums[nums < 0] = np.nan
        nums = nums.clip(upper=100)
        return nums.round(2).astype("Float64")

    if name == "gpa":
        nums[(nums < 0) | (nums > 4)] = np.nan
        return nums.round(2).astype("Float64")

    return pd.to_numeric(col, errors="coerce")


def parse_date(x):
    if pd.isna(x):
        return pd.NaT

    x = str(x).strip()
    if x == "":
        return pd.NaT

    if re.fullmatch(r"\d{10}", x):
        return pd.to_datetime(int(x), unit="s", errors="coerce")

    if re.fullmatch(r"\d{13}", x):
        return pd.to_datetime(int(x), unit="ms", errors="coerce")

    d = pd.to_datetime(x, errors="coerce", format="mixed")
    if pd.isna(d):
        d = pd.to_datetime(x, errors="coerce", dayfirst=True)
    return d


def fix_email(x):
    x = clean_text(x)
    if pd.isna(x):
        return np.nan, False

    x = str(x).strip().lower()
    ok = bool(email_pattern.fullmatch(x))

    if ok:
        return x, True
    else:
        return np.nan, False


def fix_phone(x):
    x = clean_text(x)
    if pd.isna(x):
        return np.nan, False

    x = str(x).strip()
    x = re.sub(r"(?i)(ext\.?|x)\s*\d+\b", "", x).strip()
    digits = re.sub(r"\D", "", x)

    if digits.startswith("001") and len(digits) == 13:
        digits = digits[2:]

    if digits.startswith("998") and len(digits) == 12:
        return "+" + digits, True

    if len(digits) == 9:
        return "+998" + digits, True

    if digits.startswith("1") and len(digits) == 11:
        return "+" + digits, True

    if len(digits) == 10:
        return "+1" + digits, True

    return np.nan, False


def read_json(x):
    x = clean_text(x)
    if pd.isna(x):
        return None

    x = str(x).strip()

    if x == "INVALID_JSON_DATA":
        return None

    try:
        return json.loads(x)
    except:
        pass

    try:
        return json.loads(x.replace("'", '"'))
    except:
        pass

    x2 = re.sub(r'([{,]\s*)([A-Za-z_][A-Za-z0-9_]*)(\s*:)', r'\1"\2"\3', x)
    x2 = x2.replace("'", '"')
    try:
        return json.loads(x2)
    except:
        pass

    try:
        return ast.literal_eval(x)
    except:
        pass

    x3 = re.sub(r'([{,]\s*)([A-Za-z_][A-Za-z0-9_]*)(\s*:)', r"\1'\2'\3", x)
    try:
        return ast.literal_eval(x3)
    except:
        return None


def split_profile(obj):
    if not isinstance(obj, dict):
        return {
            "hobbies": np.nan,
            "skills": np.nan,
            "family": np.nan,
            "devices": np.nan,
            "skills_python": pd.NA,
            "skills_excel": pd.NA,
            "skills_sql": pd.NA,
            "skills_soft": np.nan,
            "family_siblings": pd.NA,
            "family_income_father": pd.NA,
            "family_income_mother": pd.NA,
            "device_types": np.nan,
            "device_brands": np.nan,
            "device_years": np.nan
        }

    hobbies = obj.get("hobbies")
    skills = obj.get("skills")
    family = obj.get("family")
    devices = obj.get("devices")

    tech = skills.get("tech", {}) if isinstance(skills, dict) else {}
    soft = skills.get("soft") if isinstance(skills, dict) else None
    income = family.get("income", {}) if isinstance(family, dict) else {}

    device_types = []
    device_brands = []
    device_years = []

    if isinstance(devices, list):
        for item in devices:
            if isinstance(item, dict):
                if item.get("type") is not None:
                    device_types.append(str(item.get("type")))
                if item.get("brand") is not None:
                    device_brands.append(str(item.get("brand")))
                if item.get("year") is not None:
                    device_years.append(str(item.get("year")))

    return {
        "hobbies": "|".join(map(str, hobbies)) if isinstance(hobbies, list) else np.nan,
        "skills": json.dumps(skills, ensure_ascii=False) if isinstance(skills, (dict, list)) else np.nan,
        "family": json.dumps(family, ensure_ascii=False) if isinstance(family, (dict, list)) else np.nan,
        "devices": json.dumps(devices, ensure_ascii=False) if isinstance(devices, (dict, list)) else np.nan,
        "skills_python": pd.to_numeric(tech.get("python"), errors="coerce"),
        "skills_excel": pd.to_numeric(tech.get("excel"), errors="coerce"),
        "skills_sql": pd.to_numeric(tech.get("sql"), errors="coerce"),
        "skills_soft": "|".join(map(str, soft)) if isinstance(soft, list) else np.nan,
        "family_siblings": pd.to_numeric(family.get("siblings"), errors="coerce") if isinstance(family, dict) else pd.NA,
        "family_income_father": pd.to_numeric(income.get("father"), errors="coerce") if isinstance(income, dict) else pd.NA,
        "family_income_mother": pd.to_numeric(income.get("mother"), errors="coerce") if isinstance(income, dict) else pd.NA,
        "device_types": "|".join(device_types) if device_types else np.nan,
        "device_brands": "|".join(device_brands) if device_brands else np.nan,
        "device_years": "|".join(device_years) if device_years else np.nan
    }


def split_address(x):
    x = clean_text(x)
    if pd.isna(x):
        return {"addr_city": np.nan, "addr_district": np.nan, "addr_postal": np.nan}

    x = str(x).strip()

    if "BROKEN" in x.upper():
        return {"addr_city": np.nan, "addr_district": np.nan, "addr_postal": np.nan}

    city = np.nan
    district = np.nan
    postal = np.nan

    m = re.search(r"\b(100\d{3})\b", x)
    if m:
        postal = m.group(1)

    if "Tashkent" in x:
        city = "Tashkent"

        m = re.search(r",\s*([^,]+district)\s*,\s*Tashkent", x, flags=re.I)
        if m:
            district = m.group(1).strip()
        else:
            m = re.search(r"Tashkent\s+(.+)$", x)
            if m:
                district = m.group(1).strip()
            else:
                first = x.split(",")[0].strip()
                if first and not first.lower().startswith("apartment"):
                    district = re.sub(r"\s+\d+-kv.*$", "", first, flags=re.I).strip()
    else:
        parts = [p.strip() for p in x.split(",") if p.strip()]
        if parts:
            city = parts[-1]
            if len(parts) >= 2:
                district = parts[-2]

    return {"addr_city": city, "addr_district": district, "addr_postal": postal}


def main():
    df = pd.read_csv(INPUT_FILE)

    print("STEP 1: DATA BILAN TANISHISH")
    print(df.head(10))
    print("\nColumn names:")
    print(df.columns.tolist())
    print("\nColumn count:", df.shape[1])
    print("\nMissing values:")
    print(df.isna().sum())

    original_rows = len(df)

    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = df[col].map(clean_text)

    for col in ["age", "score", "attendance", "gpa", "money_spent"]:
        df[col] = clean_numeric(df[col], col)

    for col in ["date_of_join", "event_time"]:
        df[col] = df[col].map(parse_date)

    email_result = df["email"].apply(fix_email)
    df["email"] = email_result.apply(lambda x: x[0])
    df["email_valid"] = email_result.apply(lambda x: x[1])

    phone_result = df["phone"].apply(fix_phone)
    df["phone"] = phone_result.apply(lambda x: x[0])
    df["phone_valid"] = phone_result.apply(lambda x: x[1])

    parsed = df["profile_json"].apply(read_json)
    df["profile_json_parsed"] = parsed.apply(
        lambda x: json.dumps(x, ensure_ascii=False) if isinstance(x, (dict, list)) else np.nan
    )

    profile_df = pd.DataFrame([split_profile(x) for x in parsed], index=df.index)
    df = pd.concat([df, profile_df], axis=1)

    address_df = pd.DataFrame([split_address(x) for x in df["address_raw"]], index=df.index)
    df = pd.concat([df, address_df], axis=1)

    before = len(df)
    df = df.drop_duplicates().copy()
    removed_duplicates = before - len(df)

    df["name"] = df["name"].fillna("Unknown")

    df["gender"] = df["gender"].replace({
        "male": "Male",
        "Male": "Male",
        "MALE": "Male",
        "female": "Female",
        "Female": "Female",
        "FEMALE": "Female",
        "fmale": "Female",
        "femlae": "Female"
    }).fillna("Unknown")

    course_map = {
        "Data Science": "Data Science",
        "DATA SCIENCE": "Data Science",
        "data science": "Data Science",
        "data-sciens": "Data Science",
        "data_sciense": "Data Science",
        "ds": "Data Science",
        "d.s.": "Data Science",
        "python": "Python",
        "PYTHNO": "Python",
        "Pyhton": "Python"
    }
    df["course"] = df["course"].apply(lambda x: course_map.get(x, "Other"))
    df["status"] = df["status"].astype("string").str.strip().str.lower()

    for col in ["age", "score", "attendance", "gpa"]:
        med = df[col].dropna().median()
        if pd.notna(med):
            if str(df[col].dtype) == "Int64":
                df[col] = df[col].fillna(int(round(med))).astype("Int64")
            else:
                df[col] = df[col].fillna(float(med))

    df["attendance"] = pd.to_numeric(df["attendance"], errors="coerce").round(2).astype("Float64")
    df["gpa"] = pd.to_numeric(df["gpa"], errors="coerce").round(2).astype("Float64")
    df["money_spent"] = pd.to_numeric(df["money_spent"], errors="coerce").round(2).astype("Float64")

    df["remarks"] = df["remarks"].astype("string").str.strip()
    mode_remarks = df["remarks"].dropna().mode()
    if len(mode_remarks) > 0:
        df["remarks"] = df["remarks"].fillna(mode_remarks.iloc[0])

    df["student_id"] = pd.to_numeric(df["student_id"], errors="coerce").astype("Int64")

    for col in [
        "skills_python", "skills_excel", "skills_sql",
        "family_siblings", "family_income_father", "family_income_mother"
    ]:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Float64")

    df["addr_postal"] = df["addr_postal"].astype("string")
    df["phone"] = df["phone"].astype("string")
    df["email"] = df["email"].astype("string")

    for col in ["date_of_join", "event_time"]:
        df[col] = pd.to_datetime(df[col], errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S")

    df.to_csv(OUTPUT_FILE, index=False)

    print("\nSTEP 10: QA CHECKS")
    print("Original rows:", original_rows)
    print("Cleaned rows:", len(df))
    print("Removed duplicates:", removed_duplicates)
    print("Missing email:", int(df["email"].isna().sum()))
    print("Missing phone:", int(df["phone"].isna().sum()))
    print("Score range OK:", bool(df["score"].dropna().between(0, 100).all()))
    print("Attendance range OK:", bool(df["attendance"].dropna().between(0, 100).all()))
    print("GPA range OK:", bool(df["gpa"].dropna().between(0, 4).all()))
    print("Duplicate rows after cleaning:", int(df.duplicated().sum()))
    print("\nCleaned file saved as:", OUTPUT_FILE)


if __name__ == "__main__":
    main()