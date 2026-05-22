import pandas as pd
import re

# Load the raw sequencing CSV
df = pd.read_csv("data cleaners/Course Sequencing.csv")

# Filter out empty rows and isolate the rows that contain sequencing definitions
rules = df[df["Unnamed: 2"].astype(str).str.contains("Sequence", na=False)][
    "Unnamed: 2"
].tolist()

cleaned_pairs = []

# Loop through every sequencing rule string
for rule in rules:
    # Match the prerequisite pattern: "Sequence [Course A] before [Course B, Course C...]"
    match = re.match(r"Sequence\s+(.*?)\s+before\s+(.*)", rule)
    if match:
        # Strip whitespaces and potential quote wrapper anomalies from the CSV export
        first_course = match.group(1).replace('"', "").strip()
        second_courses_raw = match.group(2).replace('"', "").strip()

        # Split multiple trailing courses by their commas
        second_courses = [
            c.strip() for c in second_courses_raw.split(",") if c.strip()
        ]

        # Dynamically append a new individual row for each dependent course pair
        for second_course in second_courses:
            cleaned_pairs.append(
                {
                    "Prerequisite": first_course,
                    "Subsequent_Course": second_course,
                }
            )

# Create the final flat 2-column DataFrame
sequencing_df = pd.DataFrame(cleaned_pairs)

# Save the updated data directly to your working folder
sequencing_df.to_csv("data cleaners/course_sequencing_cleaned.csv", index=False)

print(
    f"Successfully processed {len(sequencing_df)} individual sequence constraints!"
)