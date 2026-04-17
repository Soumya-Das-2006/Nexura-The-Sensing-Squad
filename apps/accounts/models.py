from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone


mobile_validator = RegexValidator(
	regex=r"^\d{10}$",
	message="Mobile number must be a 10-digit number.",
)

USER_LANGUAGE_CHOICES = [
	("en", "English"),
	("hi", "हिंदी (Hindi)"),
	("mr", "मराठी (Marathi)"),
	("bn", "বাংলা (Bengali)"),
	("ta", "தமிழ் (Tamil)"),
	("te", "తెలుగు (Telugu)"),
]


class UserManager(BaseUserManager):
	def _normalize_mobile(self, mobile: str) -> str:
		value = (mobile or "").strip().lstrip("+")
		if value.startswith("91") and len(value) > 10:
			value = value[2:]
		return value.lstrip("0")

	def create_user(self, mobile, password=None, **extra_fields):
		if not mobile:
			raise ValueError("The mobile field is required.")

		mobile = self._normalize_mobile(mobile)
		user = self.model(mobile=mobile, **extra_fields)
		user.set_password(password)
		user.save(using=self._db)
		return user

	def create_superuser(self, mobile, password=None, **extra_fields):
		extra_fields.setdefault("is_staff", True)
		extra_fields.setdefault("is_superuser", True)
		extra_fields.setdefault("is_admin", True)

		if extra_fields.get("is_staff") is not True:
			raise ValueError("Superuser must have is_staff=True.")
		if extra_fields.get("is_superuser") is not True:
			raise ValueError("Superuser must have is_superuser=True.")

		return self.create_user(mobile, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
	LANGUAGE_CHOICES = USER_LANGUAGE_CHOICES

	mobile = models.CharField(max_length=10, unique=True, validators=[mobile_validator])
	email = models.EmailField(blank=True, null=True)

	is_worker = models.BooleanField(default=True)
	is_admin = models.BooleanField(default=False)

	is_staff = models.BooleanField(default=False)
	is_active = models.BooleanField(default=True)

	mobile_verified = models.BooleanField(default=False)
	profile_complete = models.BooleanField(default=False)
	language = models.CharField(max_length=5, choices=LANGUAGE_CHOICES, default="en")

	date_joined = models.DateTimeField(auto_now_add=True)

	objects = UserManager()

	USERNAME_FIELD = "mobile"
	REQUIRED_FIELDS = []

	class Meta:
		ordering = ["-date_joined"]

	def __str__(self):
		return self.mobile

	@property
	def display_name(self):
		profile = getattr(self, "workerprofile", None)
		if profile and getattr(profile, "name", ""):
			return profile.name
		return self.mobile

	def save(self, *args, **kwargs):
		if self.is_admin and not self.is_staff:
			self.is_staff = True
		super().save(*args, **kwargs)


class OTPRecord(models.Model):
	PURPOSE_CHOICES = [
		("register", "Register"),
		("login", "Login"),
	]

	mobile = models.CharField(max_length=10, db_index=True, validators=[mobile_validator])
	code = models.CharField(max_length=6)
	purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES, default="login")

	created_at = models.DateTimeField(auto_now_add=True)
	expires_at = models.DateTimeField(db_index=True)

	verified = models.BooleanField(default=False)
	attempts = models.PositiveSmallIntegerField(default=0)

	class Meta:
		ordering = ["-created_at"]

	def __str__(self):
		return f"{self.mobile} ({self.purpose})"

	@property
	def is_expired(self):
		return timezone.now() >= self.expires_at


class KYCRecord(models.Model):
	STATUS_CHOICES = [
		("pending", "Pending"),
		("in_review", "In Review"),
		("approved", "Approved"),
		("rejected", "Rejected"),
	]

	worker = models.OneToOneField(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="kyc",
	)
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

	aadhaar_number = models.CharField(max_length=20, blank=True)
	pan_number = models.CharField(max_length=20, blank=True)
	document_front_url = models.URLField(blank=True)
	document_back_url = models.URLField(blank=True)

	submitted_at = models.DateTimeField(blank=True, null=True)
	verified_at = models.DateTimeField(blank=True, null=True)
	remarks = models.TextField(blank=True)

	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["-created_at"]

	def __str__(self):
		return f"KYC<{self.worker.mobile}>:{self.status}"

	def set_aadhaar(self, raw_aadhaar):
		from django.contrib.auth.hashers import make_password
		self.aadhaar_number = make_password(raw_aadhaar)
