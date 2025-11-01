from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone


class AccessCode(models.Model):
    """Single-use code required for account creation."""

    code = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(null=True, blank=True)
    used_by = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assessment_access_code",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        status = "used" if self.is_used else "unused"
        return f"{self.code} ({status})"

    @property
    def is_used(self) -> bool:
        return self.used_by_id is not None

    def mark_used(self, user) -> None:
        self.used_by = user
        self.used_at = timezone.now()
        self.save(update_fields=["used_by", "used_at"])


class UserProfile(models.Model):
    """Lightweight per-user quota tracking."""

    DEFAULT_RUN_ALLOWANCE = 5

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="assessment_profile",
    )
    runs_remaining = models.PositiveSmallIntegerField(default=DEFAULT_RUN_ALLOWANCE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["user__username"]

    def __str__(self) -> str:
        return f"{self.user} - {self.runs_remaining} runs left"

    def decrement_run(self) -> bool:
        if self.runs_remaining <= 0:
            return False
        self.runs_remaining -= 1
        self.save(update_fields=["runs_remaining", "updated_at"])
        return True


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def ensure_user_profile(sender, instance, created, **kwargs):
    """Create an assessment profile whenever a new user account is created."""
    if created:
        UserProfile.objects.create(user=instance)
