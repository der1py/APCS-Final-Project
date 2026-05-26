from models.course import Course
from models.rules import Rules
from models.student import Student
from data_loader import load_students, load_courses

# =====================================================
# INPUT DATA
# =====================================================

students = load_students()

blocks = list(range(8))

courses = load_courses()

# =====================================================
# DISPLAY DATA
# =====================================================

print("STUDENTS")
for s in students:
    print(s)

print("Number of students:", len(students))

print("\nCOURSES")
for c in courses:
    print(c)

print("Number of courses:", len(courses))