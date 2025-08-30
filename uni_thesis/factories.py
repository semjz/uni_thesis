import factory
from .models import Professor, Student, User, ThesisDefenceRequest, TimeSlot, DefenceSession
from .utils import random_numeric_string
from datetime import date as _date, datetime, timedelta, time as _time

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

    user = factory.SubFactory(UserFactory, role="Professor")
    field_of_study = factory.Iterator(["math", "physics", "computer science"])
    specialization = factory.Faker("job")

class StudentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Student

    user = factory.SubFactory(UserFactory, role="Student")
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
    field = factory.LazyAttribute(lambda o: o.student.field_of_study)


# ----------------------------
# TimeSlotFactory
# ----------------------------
class TimeSlotFactory(factory.django.DjangoModelFactory):
    """
    Creates a professor time slot. Defaults to a 1-hour future slot and available=True.
    Uniqueness: (professor, date, start_time)
    """
    class Meta:
        model = TimeSlot
        # Helps avoid IntegrityError on the unique constraint in repeated tests
        django_get_or_create = ("professor", "date", "start_time")

    professor = factory.SubFactory(ProfessorFactory)
    # future date within 30 days
    date = factory.Faker("date_between", start_date="today", end_date="+30d")

    # Simple rotating times (9:00, 10:00, 11:00) to reduce unique collisions
    start_time = factory.Iterator([_time(9, 0), _time(10, 0), _time(11, 0)])

    # End = start + 1 hour
    @factory.lazy_attribute
    def end_time(self):
        return (datetime.combine(_date.today(), self.start_time) + timedelta(hours=1)).time()

    available = True

    class Params:
        # mark slot as already booked (available=False)
        booked = factory.Trait(available=False)


# ----------------------------
# DefenceSessionFactory
# ----------------------------
class DefenceSessionFactory(factory.django.DjangoModelFactory):
    """
    Creates a DefenceSession with two different professors and a valid time window.
    Also ensures BOTH professors have a matching TimeSlot, marked as booked (available=False).
    """

    class Meta:
        model = DefenceSession

    # Ensure the request has its `field` set (required by your model)
    request = factory.SubFactory(ThesisDefenceRequestFactory)

    # Times: default to a consistent 1h window in the near future
    date = factory.Faker("date_between", start_date="today", end_date="+20d")
    start_time = factory.LazyFunction(lambda: _time(9, 0))
    end_time = factory.LazyAttribute(
        lambda obj: (datetime.combine(_date.today(), obj.start_time) + timedelta(hours=1)).time()
    )
    location = factory.Faker("sentence", nb_words=2)

    # Professors: different people; align their field to the request's field for realism
    @factory.lazy_attribute
    def evaluator(self) -> Professor:
        req: ThesisDefenceRequest = self.request
        return ProfessorFactory(field_of_study=req.field)

    @factory.lazy_attribute
    def observer(self) -> Professor:
        req: ThesisDefenceRequest = self.request
        prof = ProfessorFactory(field_of_study=req.field)
        # Very unlikely, but ensure distinct from evaluator
        if prof.id == self.evaluator.id:
            prof = ProfessorFactory(field_of_study=req.field)
        return prof

    @factory.post_generation
    def _ensure_booked_slots(self, create, extracted, **kwargs):
        """
        After creating the session, create/get matching TimeSlots for both professors
        and mark them booked (available=False). This mirrors real booking behavior.
        """
        if not create:
            return

        # Evaluator slot
        eval_slot, _ = TimeSlot.objects.get_or_create(
            professor=self.evaluator,
            date=self.date,
            start_time=self.start_time,
            defaults={"end_time": self.end_time, "available": False},
        )
        # If an available slot existed, book it now
        if eval_slot.available:
            eval_slot.available = False
            # keep end_time in sync with the session time
            eval_slot.end_time = self.end_time
            eval_slot.save(update_fields=["available", "end_time"])

        # Observer slot
        obs_slot, _ = TimeSlot.objects.get_or_create(
            professor=self.observer,
            date=self.date,
            start_time=self.start_time,
            defaults={"end_time": self.end_time, "available": False},
        )
        if obs_slot.available:
            obs_slot.available = False
            obs_slot.end_time = self.end_time
            obs_slot.save(update_fields=["available", "end_time"])

    class Params:
        # Trait: create available (not booked) timeslots instead of booking them
        # Useful if you want to test the booking behavior in the API separately.
        with_available_slots = factory.Trait(
            _ensure_booked_slots=factory.PostGenerationMethodCall("_make_available_slots")
        )

    def _make_available_slots(self, create, extracted, **kwargs):
        """
        Optional helper used by the 'with_available_slots' trait to create matching
        available=True slots (instead of booked). Keeps session creation independent.
        """
        if not create:
            return
        # Ensure the slot rows exist as available=True
        TimeSlot.objects.get_or_create(
            professor=self.evaluator,
            date=self.date,
            start_time=self.start_time,
            defaults={"end_time": self.end_time, "available": True},
        )
        TimeSlot.objects.get_or_create(
            professor=self.observer,
            date=self.date,
            start_time=self.start_time,
            defaults={"end_time": self.end_time, "available": True},
        )
