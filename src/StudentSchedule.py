class StudentSchedule:
    def __init__(self, student_id, student_name):
        self.student_id = student_id
        self.student_name = student_name

        # Dictionary format:
        # key = block/period
        # value = course name/code
        self.schedule = {}

    # Add a course to a specific block
    def add_course(self, block, course):
        self.schedule[block] = course

    # Remove a course from a block
    def remove_course(self, block):
        if block in self.schedule:
            del self.schedule[block]

    # Get course in a specific block
    def get_course(self, block):
        return self.schedule.get(block, None)

    # Print the full schedule
    def print_schedule(self):
        print(f"Schedule for {self.student_name} ({self.student_id})")

        if len(self.schedule) == 0:
            print("No courses assigned.")
            return

        for block, course in sorted(self.schedule.items()):
            print(f"Block {block}: {course}")

    # String representation
    def __str__(self):
        output = f"Student: {self.student_name} ({self.student_id})\n"

        if len(self.schedule) == 0:
            output += "No courses assigned."
        else:
            for block, course in sorted(self.schedule.items()):
                output += f"Block {block}: {course}\n"

        return output