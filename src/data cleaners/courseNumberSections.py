import pandas as pd

# Load the CSV
df = pd.read_csv("data cleaners/Course Number of Sections.csv")

# 1. Filter out empty rows and the repeating text header rows
df_cleaned = df[df["Course"].notna() & (df["Course"].str.strip() != "Course")].copy()

# 2. Realign the shifted data: if 'Unnamed: 5' exists, use it to fill the missing Sections
if "Unnamed: 5" in df_cleaned.columns:
    df_cleaned["Sections"] = df_cleaned["Sections"].fillna(df_cleaned["Unnamed: 5"])

# 3. Keep only the requested columns
df_cleaned = df_cleaned[["Course", "Description", "Sections"]]

# 4. Clean up text whitespace formatting
df_cleaned["Course"] = df_cleaned["Course"].astype(str).str.strip()
df_cleaned["Description"] = df_cleaned["Description"].astype(str).str.strip()

# 5. Convert sections safely (coerce errors to NaN, fill with 0, then cast to int)
df_cleaned["Sections"] = (
    pd.to_numeric(df_cleaned["Sections"], errors="coerce").fillna(0).astype(int)
)

# Save to a perfectly cleaned CSV
df_cleaned.to_csv("data cleaners/course_sections_cleaned.csv", index=False)

print(
    f"Success! Cleaned file saved with {len(df_cleaned)} valid course entries."
)