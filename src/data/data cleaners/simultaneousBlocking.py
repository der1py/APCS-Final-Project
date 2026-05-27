import pandas as pd
import re

# Load the raw blocking rules CSV
df = pd.read_csv("data cleaners/course Simultaneous Blocking.csv")

# Filter rows that contain scheduling rules
rules = df[df["Unnamed: 2"].astype(str).str.contains("Schedule", na=False)][
    "Unnamed: 2"
].tolist()

cleaned_blocking_pairs = []

# Loop through every rule statement
for rule in rules:
    # Match pattern: "Schedule [Course list] in a [Blocking Type] blocking"
    match = re.match(r"Schedule\s+(.*?)\s+in a (.*?) blocking", rule)
    if match:
        courses_raw = match.group(1).replace('"', "").strip()
        blocking_type = match.group(2).strip()

        # Split the group of courses by commas
        courses = [c.strip() for c in courses_raw.split(",") if c.strip()]

        # Generate separate pairing records down the column if there are multiple items
        if len(courses) >= 2:
            first_course = courses[0]
            for subsequent_course in courses[1:]:
                cleaned_blocking_pairs.append(
                    {
                        "Course_1": first_course,
                        "Course_2": subsequent_course,
                        "Blocking_Type": blocking_type,
                    }
                )

# Convert to a flat DataFrame
blocking_df = pd.DataFrame(cleaned_blocking_pairs)

# Save to a new structured CSV file
blocking_df.to_csv("cleaned data/course_blocking_cleaned.csv", index=False)

print(
    f"Successfully flattened and generated {len(blocking_df)} constraint records!"
)