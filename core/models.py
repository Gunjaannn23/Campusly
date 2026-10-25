from django.conf import settings
from django.db import models

CATEGORIES = ["Marketplace", "Rooms", "Gigs", "Events"]
CONDITIONS = ["New", "Like new", "Good", "Fair"]


class EmailCode(models.Model):
    """One-time sign-in code. Only a hash of the code is stored."""
    MODES = (("in", "Sign in"), ("up", "Create account"))
    email = models.EmailField(db_index=True)
    code_hash = models.CharField(max_length=64)
    full_name = models.CharField(max_length=60, blank=True)
    mode = models.CharField(max_length=2, choices=MODES, default="in")
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    used = models.BooleanField(default=False)

    def __str__(self):
        return "%s (%s)" % (self.email, self.created_at)


class Listing(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="listings")
    category = models.CharField(max_length=20, choices=[(c, c) for c in CATEGORIES])
    title = models.CharField(max_length=60)
    price = models.CharField(max_length=20, blank=True)
    place = models.CharField(max_length=40, blank=True)
    details = models.CharField(max_length=160, blank=True)
    contact = models.CharField(max_length=60, blank=True)
    author_name = models.CharField(max_length=60, blank=True)
    condition = models.CharField(max_length=20, blank=True)
    status = models.CharField(max_length=10, default="active", choices=[("active", "active"), ("sold", "sold")])
    photo = models.FileField(upload_to="listing_photos/%Y/%m/", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class Message(models.Model):
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_messages")
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="received_messages")
    sender_name = models.CharField(max_length=60, blank=True)
    body = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return "%s -> %s" % (self.sender_id, self.recipient_id)
