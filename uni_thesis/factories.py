import factory
from .models import Professor, Student, User, ThesisDefenceRequest
from .utils import random_numeric_string

class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        exclude = ("phone_number1",)

    phone_number1 = factory.Faker("phone_number", locale="fa_IR")
    phone_number = factory.LazyAttribute(lambda o: o.phone_number1.replace(" ", "")[:13])
    first_name = factory.Faker("first_name", locale="fa_IR")
    last_name = factory.Faker("last_name", locale="fa_IR")
    email = factory.LazyAttribute(lambda o: f"{o.uni_id}@university.edu")
    gender = factory.Iterator(["male", "female"])
    birth_date = factory.Faker("date", locale="fa_IR")
    role = factory.Iterator(["Student", "Professor", "Admin"])
    password = factory.Faker("password")

    @factory.lazy_attribute
    def uni_id(self):
        return random_numeric_string(10)

    @factory.lazy_attribute
    def national_code(self):
        return random_numeric_string(10)


class ProfessorFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Professor

    user = factory.SubFactory(UserFactory)
    field_of_study = factory.Iterator(["math", "physics", "computer science"])
    specialization = factory.Faker("job")

class StudentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Student

    user = factory.SubFactory(UserFactory)
    field_of_study = factory.Iterator(["math", "physics", "computer science"])
    level_of_study = factory.Iterator(["BSc", "MSc", "PhD"])
    specialization = factory.Faker("job")

class ThesisDefenceRequestFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ThesisDefenceRequest

    student = factory.SubFactory(StudentFactory)
    thesis_title = factory.Faker("sentence", nb_words=4)
    thesis_abstract = factory.Faker("sentence", nb_words=10)
    created_at = factory.Faker("date_this_year")