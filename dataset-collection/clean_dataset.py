import glob
import hashlib
import os
import unicodedata

import pandas as pd

RAW_DIR = "data/raw"
CLEAN_DIR = "data/clean"


def normalize_text_series(s: pd.Series) -> pd.Series:
    def norm(v):
        if not isinstance(v, str):
            return v
        v = unicodedata.normalize("NFKC", v)
        return v.strip()

    return s.map(norm)


def normalize_text_columns(df: pd.DataFrame) -> pd.DataFrame:
    for col in df.select_dtypes(include="object").columns:
        df[col] = normalize_text_series(df[col])
    return df


def row_hash(df: pd.DataFrame) -> pd.Series:
    return df.astype(str).apply(lambda row: hashlib.md5("|".join(row).encode("utf-8")).hexdigest(), axis=1)


def dedup_report(df: pd.DataFrame, id_col: str | None, label: str) -> pd.DataFrame:
    before = len(df)
    df = df.drop_duplicates()
    exact_dupes = before - len(df)
    print(f"  [{label}] exact duplicate rows removed: {exact_dupes}")

    if id_col:
        before2 = len(df)
        df = df.drop_duplicates(subset=[id_col])
        id_dupes = before2 - len(df)
        print(f"  [{label}] duplicate '{id_col}' rows removed: {id_dupes}")
    else:
        before2 = len(df)
        h = row_hash(df)
        df = df[~h.duplicated()]
        hash_dupes = before2 - len(df)
        print(f"  [{label}] duplicate rows by content-hash removed: {hash_dupes}")

    return df


def print_raw_structure(df: pd.DataFrame, label: str) -> None:
    print(f"\n{'=' * 90}\n{label}\n{'=' * 90}")
    print(f"rows: {len(df)}, columns: {len(df.columns)}")
    print("\ndtypes:")
    print(df.dtypes.to_string())
    print("\nnull counts:")
    nulls = df.isnull().sum()
    nz = nulls[nulls > 0]
    print(nz.to_string() if len(nz) else "  none")


def clean_doomscrolling(df: pd.DataFrame, filename: str, label: str) -> pd.DataFrame:
    df = dedup_report(df, id_col="ResponseId", label=label)
    df = normalize_text_columns(df)
    df["RecordedDate"] = pd.to_datetime(df["RecordedDate"])
    df["StartDate"] = pd.to_datetime(df["StartDate"])
    df["EndDate"] = pd.to_datetime(df["EndDate"])
    df["source_dataset"] = filename
    return df


def clean_social_media_addiction(df: pd.DataFrame, filename: str, label: str) -> pd.DataFrame:
    before = len(df)
    essential = [c for c in df.columns if c != "gender"]
    fully_null_mask = df[essential].isnull().all(axis=1)
    n_junk = int(fully_null_mask.sum())
    df = df[~fully_null_mask].copy()
    print(f"  [{label}] dropped {n_junk} fully-null row(s) (no usable data)")

    df = dedup_report(df, id_col=None, label=label)

    df = normalize_text_columns(df)

    n_gender_null = int(df["gender"].isnull().sum())
    df["gender"] = df["gender"].fillna("Unknown")
    print(f"  [{label}] {n_gender_null} row(s) had null gender -> labeled 'Unknown' (kept, per user decision)")

    n_insta = int((df["platform_usage"] == "Insta").sum())
    df["platform_usage"] = df["platform_usage"].replace({"Insta": "Instagram"})
    print(f"  [{label}] merged {n_insta} 'Insta' row(s) into 'Instagram' (per user decision)")

    df["age"] = df["age"].astype(int)
    df["source_dataset"] = filename
    return df


def clean_reels(df: pd.DataFrame, filename: str, label: str) -> pd.DataFrame:
    df = dedup_report(df, id_col="user_id", label=label)
    df = normalize_text_columns(df)
    df["source_dataset"] = filename
    return df


CLEANERS = {
    "Doomscrolling_Study2_Dataset.csv": clean_doomscrolling,
    "Doomscrolling_Study3_Dataset.csv": clean_doomscrolling,
    "Social_Media_Addiction.csv": clean_social_media_addiction,
    "reels_attention_span_dataset_12000.csv": clean_reels,
}

CATEGORY_COLUMN = {
    "Doomscrolling_Study2_Dataset.csv": "Gender",
    "Doomscrolling_Study3_Dataset.csv": "Gender",
    "Social_Media_Addiction.csv": "platform_usage",
    "reels_attention_span_dataset_12000.csv": "platform",
}


def main():
    os.makedirs(CLEAN_DIR, exist_ok=True)
    raw_files = sorted(glob.glob(os.path.join(RAW_DIR, "*.csv")))

    cleaned = {}

    print("#" * 90)
    print("STEP 1: RAW STRUCTURE")
    print("#" * 90)
    raw_dfs = {}
    for path in raw_files:
        filename = os.path.basename(path)
        df = pd.read_csv(path)
        raw_dfs[filename] = df
        print_raw_structure(df, filename)

    print("\n" + "#" * 90)
    print("STEP 2-3: CLEANING")
    print("#" * 90)
    for filename, df in raw_dfs.items():
        label = filename
        print(f"\n--- cleaning {label} ---")
        cleaner = CLEANERS[filename]
        cleaned_df = cleaner(df.copy(), filename, label)
        cleaned[filename] = cleaned_df
        out_path = os.path.join(CLEAN_DIR, filename)
        cleaned_df.to_csv(out_path, index=False)
        print(f"  [{label}] wrote {len(cleaned_df)} rows -> {out_path}")

    print("\n" + "#" * 90)
    print("STEP 4: POST-CLEAN SUMMARY")
    print("#" * 90)
    for filename, df in cleaned.items():
        print(f"\n--- {filename} ---")
        print(f"final row count: {len(df)}")
        print(f"columns kept ({len(df.columns)}): {list(df.columns)}")
        cat_col = CATEGORY_COLUMN.get(filename)
        if cat_col and cat_col in df.columns:
            print(f"\nfrequency breakdown by '{cat_col}':")
            print(df[cat_col].value_counts(dropna=False).to_string())

    combined = pd.concat(cleaned.values(), ignore_index=True, sort=False)
    print(f"\n--- COMBINED ---")
    print(f"final row count: {len(combined)}")
    print(f"columns kept ({len(combined.columns)}): {list(combined.columns)}")
    print("\nfrequency breakdown by 'source_dataset':")
    print(combined["source_dataset"].value_counts().to_string())

    print("\n" + "#" * 90)
    print("STEP 5: df.head() PER CLEANED DATASET")
    print("#" * 90)
    for filename, df in cleaned.items():
        print(f"\n--- {filename} ---")
        print(df.head().to_string())


if __name__ == "__main__":
    main()
