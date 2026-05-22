import pandas as pd

# Load the original CSV without a fixed header
df = pd.read_csv("data cleaners/cleanedstudentrequests.csv", header=None)

cleaned_data = []

# Initialize tracking variables
current_student_id = None
current_grade = None

# Loop through every row in the dataframe
for i in range(len(df)):
    row = df.iloc[i]
    first_val = str(row[0]).strip()

    # Case 1: Detect a new student info block
    if first_val == "ID":
        current_student_id = row[1]
        current_grade = row[3]
        continue  # Move to the next row

    # Case 2: Skip the table header row
    if first_val == "Course" or pd.isna(row[0]) or first_val == "":
        continue

    # Case 3: Process an actual course row
    course = row[0]
    description = row[3]

    # Check if course is an alternate (Column index 10 is the 11th column)
    alternate = False
    if len(row) > 10:
        if str(row[10]).strip().upper() == "Y":
            alternate = True

    # Only append if we have successfully mapped a student to this course
    if current_student_id is not None:
        cleaned_data.append(
            {
                "id": int(float(current_student_id)),  # Cleans up any float formatting
                "grade": int(float(current_grade)),
                "course": course,
                "description": description,
                "alternate": alternate,
            }
        )

# Create cleaned dataframe
cleaned_df = pd.DataFrame(cleaned_data)

# Save cleaned CSV
cleaned_df.to_csv("data cleaners/student_requests_cleaned.csv", index=False)

print(
    f"Cleaned file saved successfully! Processed {len(cleaned_df)} course requests."
)