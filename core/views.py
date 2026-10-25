import json
import logging
import re
import secrets
import uuid
from datetime import timedelta
from functools import wraps
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model, login, logout
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.crypto import constant_time_compare, salted_hmac
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST

from .emails import send_code_email
from .models import CATEGORIES, CONDITIONS, EmailCode, Listing, Message

log = logging.getLogger(__name__)
User = get_user_model()
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PAGES = Path(__file__).resolve().parent / "pages"
MAX_PHOTO_BYTES = 3 * 1024 * 1024


# ---------- helpers ----------
def err(message, status=400):
    return JsonResponse({"ok": False, "error": message}, status=status)


def body_json(request):
    try:
        data = json.loads(request.body.decode("utf-8") or "{}")
        return data if isinstance(data, dict) else {}
    except (ValueError, UnicodeDecodeError):
        return {}


def api_login_required(fn):
    @wraps(fn)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return err("Please sign in.", 401)
        return fn(request, *args, **kwargs)
    return wrapper


def hash_code(email, code):
    return salted_hmac("campusly.email-code", "%s:%s" % (email, code)).hexdigest()


def display_name(user):
    return user.first_name or user.email.split("@")[0]


def user_json(user):
    return {"id": str(user.pk), "email": user.email, "name": display_name(user)}


def listing_json(item):
    return {
        "id": str(item.pk),
        "user_id": str(item.user_id),
        "category": item.category,
        "title": item.title,
        "price": item.price,
        "place": item.place,
        "details": item.details,
        "contact": item.contact,
        "author_name": item.author_name,
        "condition": item.condition,
        "status": item.status,
        "photo_url": item.photo.url if item.photo else "",
        "created_at": item.created_at.isoformat(),
    }


def message_json(m):
    return {
        "id": str(m.pk),
        "listing_id": str(m.listing_id),
        "sender_id": str(m.sender_id),
        "recipient_id": str(m.recipient_id),
        "sender_name": m.sender_name,
        "body": m.body,
        "created_at": m.created_at.isoformat(),
        "listings": {"title": m.listing.title},
    }


def image_ext(upload):
    """Return a safe file extension if the upload really is an image, else None."""
    head = upload.read(12)
    upload.seek(0)
    if head.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if head.startswith(b"GIF8"):
        return "gif"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "webp"
    return None


# ---------- pages ----------
def _page(name):
    return HttpResponse((PAGES / name).read_text(encoding="utf-8"), content_type="text/html; charset=utf-8")


@never_cache
@ensure_csrf_cookie
def index(request):
    return _page("index.html")


@never_cache
@ensure_csrf_cookie
def login_page(request):
    if request.user.is_authenticated:
        return redirect("home")
    return _page("login.html")


@never_cache
@ensure_csrf_cookie
def home_page(request):
    if not request.user.is_authenticated:
        return redirect("login")
    return _page("home.html")


# ---------- auth API ----------
@require_POST
def request_code(request):
    data = body_json(request)
    email = str(data.get("email", "")).strip().lower()
    mode = "up" if data.get("mode") == "up" else "in"
    name = str(data.get("name", "")).strip()[:60]

    if not EMAIL_RE.match(email) or len(email) > 254:
        return err("Enter a valid email address.")
    if mode == "up" and len(name) < 2:
        return err("Enter your full name.")

    exists = User.objects.filter(username=email).exists()
    if mode == "in" and not exists:
        return err("No account for this email yet. Choose Create account.", 404)
    if mode == "up" and exists:
        return err("This email already has an account. Choose Sign in.", 409)

    now = timezone.now()
    if EmailCode.objects.filter(email=email, created_at__gte=now - timedelta(seconds=settings.CODE_RESEND_SECONDS)).exists():
        return err("Please wait a minute before asking for another code.", 429)
    if EmailCode.objects.filter(email=email, created_at__gte=now - timedelta(hours=1)).count() >= settings.CODE_MAX_PER_HOUR:
        return err("Too many codes requested. Try again in an hour.", 429)

    code = "%06d" % secrets.randbelow(10 ** 6)
    EmailCode.objects.filter(email=email, used=False).update(used=True)
    record = EmailCode.objects.create(
        email=email,
        code_hash=hash_code(email, code),
        full_name=name,
        mode=mode,
        expires_at=now + timedelta(minutes=settings.CODE_TTL_MINUTES),
    )
    try:
        send_code_email(email, code)
    except Exception:
        log.exception("Could not send verification email to %s", email)
        record.used = True
        record.save(update_fields=["used"])
        return err("We couldn't send the email. Check the email settings, then try again.", 502)
    return JsonResponse({"ok": True})


@require_POST
def verify_code(request):
    data = body_json(request)
    email = str(data.get("email", "")).strip().lower()
    code = str(data.get("code", "")).strip()
    if not EMAIL_RE.match(email) or not code.isdigit():
        return err("Enter the 6-digit code from the email.")

    record = EmailCode.objects.filter(email=email, used=False).order_by("-created_at").first()
    if record is None or record.expires_at < timezone.now():
        return err("That code expired. Request a new one.")
    if record.attempts >= settings.CODE_MAX_ATTEMPTS:
        return err("Too many wrong tries. Request a new code.", 429)
    if not constant_time_compare(record.code_hash, hash_code(email, code)):
        record.attempts += 1
        record.save(update_fields=["attempts"])
        left = max(0, settings.CODE_MAX_ATTEMPTS - record.attempts)
        return err("That code is wrong. %d tries left." % left)

    record.used = True
    record.save(update_fields=["used"])
    if record.mode == "up":
        user, created = User.objects.get_or_create(
            username=email, defaults={"email": email, "first_name": record.full_name}
        )
        if created:
            user.set_unusable_password()
            user.save(update_fields=["password"])
    else:
        user = User.objects.filter(username=email).first()
        if user is None:
            return err("No account for this email yet. Choose Create account.", 404)
    login(request, user)
    return JsonResponse({"ok": True, "user": user_json(user)})


@api_login_required
def me(request):
    return JsonResponse({"ok": True, "user": user_json(request.user)})


@require_POST
def logout_view(request):
    logout(request)
    return JsonResponse({"ok": True})


# ---------- listings API ----------
def clean(request, key, limit):
    return str(request.POST.get(key, "")).strip()[:limit]


@api_login_required
def listings(request):
    if request.method == "GET":
        items = Listing.objects.all()[:300]
        return JsonResponse({"ok": True, "data": [listing_json(i) for i in items]})
    if request.method != "POST":
        return err("Method not allowed.", 405)

    category = clean(request, "category", 20)
    title = clean(request, "title", 60)
    if category not in CATEGORIES:
        return err("Choose a valid category.")
    if not title:
        return err("Add a title.")
    condition = clean(request, "condition", 20)
    if category != "Marketplace" or condition not in CONDITIONS:
        condition = ""

    item = Listing(
        user=request.user,
        category=category,
        title=title,
        price=clean(request, "price", 20),
        place=clean(request, "place", 40),
        details=clean(request, "details", 160),
        contact=clean(request, "contact", 60),
        author_name=display_name(request.user),
        condition=condition,
    )
    photo = request.FILES.get("photo")
    if photo:
        if photo.size > MAX_PHOTO_BYTES:
            return err("Photo must be under 3 MB.")
        ext = image_ext(photo)
        if not ext:
            return err("Upload a JPG, PNG, GIF or WebP image.")
        photo.name = "%s.%s" % (uuid.uuid4().hex, ext)
        item.photo = photo
    item.save()
    return JsonResponse({"ok": True, "data": listing_json(item)}, status=201)


@api_login_required
def listing_detail(request, pk):
    item = Listing.objects.filter(pk=pk).first()
    if item is None:
        return err("Listing not found.", 404)
    if request.method == "DELETE":
        if item.user_id != request.user.pk:
            return err("You can only delete your own listings.", 403)
        if item.photo:
            item.photo.delete(save=False)
        item.delete()
        return JsonResponse({"ok": True})
    return err("Method not allowed.", 405)


@require_POST
@api_login_required
def listing_status(request, pk):
    item = Listing.objects.filter(pk=pk).first()
    if item is None:
        return err("Listing not found.", 404)
    if item.user_id != request.user.pk:
        return err("You can only change your own listings.", 403)
    status = body_json(request).get("status")
    if status not in ("active", "sold"):
        return err("Invalid status.")
    item.status = status
    item.save(update_fields=["status"])
    return JsonResponse({"ok": True, "data": listing_json(item)})


# ---------- messages API ----------
@api_login_required
def messages_view(request):
    user = request.user
    if request.method == "GET":
        qs = Message.objects.filter(Q(sender=user) | Q(recipient=user)).select_related("listing")[:200]
        return JsonResponse({"ok": True, "data": [message_json(m) for m in qs]})
    if request.method != "POST":
        return err("Method not allowed.", 405)

    data = body_json(request)
    text = str(data.get("body", "")).strip()[:500]
    if not text:
        return err("Write a message first.")
    try:
        listing = Listing.objects.select_related("user").get(pk=int(data.get("listing_id")))
    except (TypeError, ValueError, Listing.DoesNotExist):
        return err("Listing not found.", 404)

    if listing.user_id == user.pk:
        # Seller replying: only to someone who already messaged about this listing
        try:
            rid = int(data.get("recipient_id"))
        except (TypeError, ValueError):
            return err("Choose who to reply to.")
        if not Message.objects.filter(listing=listing, sender_id=rid, recipient=user).exists():
            return err("You can only reply to buyers who contacted you.", 403)
        recipient = User.objects.get(pk=rid)
    else:
        recipient = listing.user

    m = Message.objects.create(
        listing=listing, sender=user, recipient=recipient, sender_name=display_name(user), body=text
    )
    return JsonResponse({"ok": True, "data": message_json(m)}, status=201)
