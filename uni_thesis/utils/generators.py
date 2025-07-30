import secrets
import string

def random_numeric_string(n):
    return ''.join(secrets.choice(string.digits) for _ in range(n))

def generate_unique_uni_id(n):
    return random_numeric_string(n)

def generate_email(validated_data):
    uni_id = validated_data.get("uni_id")
    role = validated_data.get("role")


    if role == "Student":
        return f"{uni_id}.student@university.edu"

    elif role == "Professor":
        return f"{uni_id}.professor@university.edu"

    else:
        return f"{uni_id}.admin@university.edu"