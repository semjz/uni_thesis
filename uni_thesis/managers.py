from django.contrib.auth.models import BaseUserManager

class CustomUserManger(BaseUserManager):
    def create_user(self, uni_id, email, first_name, last_name, password, **extra_fields):
        if not uni_id:
            raise ValueError('uni_id must be provided')
        if not password:
            raise ValueError('password must be provided')
        email = self.normalize_email(email)
        user = self.model(uni_id=uni_id, email=email, first_name=first_name, last_name=last_name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, uni_id, email, first_name, last_name, password):
        return self.create_user(uni_id, email, first_name, last_name, password, is_staff=True, is_superuser=True)