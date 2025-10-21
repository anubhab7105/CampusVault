import uuid
import random
import string
import time

def generate_unique_id(user_type: str, length: int = 10) -> str:
    """
    Generate a unique alphanumeric ID for faculty or student.
    user_type: 'faculty' or 'student'
    length: total length of ID (default 10)
    """
    if user_type.lower() == 'faculty':
        prefix = 'F'
    elif user_type.lower() == 'student':
        prefix = 'S'
    else:
        raise ValueError("Invalid user type! Must be 'faculty' or 'student'.")

    # Create a unique base using UUID and timestamp
    unique_source = uuid.uuid4().hex + str(int(time.time() * 1000))
    
    # Shuffle and mix with random characters for uniqueness
    random_chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
    
    # Combine and ensure total length ≤ 10
    unique_id = prefix + unique_source + random_chars
    return unique_id[:length]


# Example usage
faculty_id = generate_unique_id('faculty')
student_id = generate_unique_id('student')
print("Faculty 1 \nStudent 2 ")
i=int (input("Enter your choice: "))

#Choice for output
if (i==1):
    print("Faculty ID:", faculty_id)
elif(i==2):
    print("Student ID:", student_id)
else:
    print("Wrong input")
