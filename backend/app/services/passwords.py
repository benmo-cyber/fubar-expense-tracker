import hashlib
import hmac
import secrets
import smtplib
from email.message import EmailMessage

TEMP_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789"
MIN_TEMP_LEN = 8
RESET_SECONDS = 60 * 60 * 24 * 3
FORGOT_MESSAGE = "If that email exists, a reset link was sent."
MAIL_UNAVAILABLE = "Password email is not set up yet. An admin can issue a temporary password from People."


def generate_temp_password(length: int = 10) -> str:
    return "".join(secrets.choice(TEMP_ALPHABET) for _ in range(length))


def must_change_after_issue(actor_id: str, target_id: str) -> bool:
    """Someone else must choose a new password. Issuing your own does not."""
    return str(actor_id) != str(target_id)


def validate_new_password(new_password: str, confirm: str, current: str | None = None) -> str | None:
    if len(new_password) < MIN_TEMP_LEN:
        return "Password must be at least 8 characters."
    if new_password != confirm:
        return "Passwords do not match."
    if current is not None and new_password == current:
        return "Pick a password different from the current one."
    return None


def can_send_reset(host_user: str, public_url: str) -> bool:
    return bool((host_user or "").strip() and (public_url or "").strip())


def forgot_message(mail_ready: bool) -> str:
    if mail_ready:
        return FORGOT_MESSAGE
    return MAIL_UNAVAILABLE


def make_reset_token(secret: str, user_id: str, password_hash: str, issued_at: int, ttl: int = RESET_SECONDS) -> str:
    expiry = int(issued_at) + int(ttl)
    payload = f"{user_id}.{expiry}"
    signature = hmac.new(secret.encode(), f"{payload}.{password_hash}".encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{signature}"


def read_reset_token(secret: str, token: str, password_hash: str, now: int) -> str | None:
    parts = (token or "").split(".")
    if len(parts) != 3:
        return None
    user_id, expiry_text, signature = parts
    try:
        expiry = int(expiry_text)
    except ValueError:
        return None
    if int(now) > expiry:
        return None
    payload = f"{user_id}.{expiry}"
    expected = hmac.new(secret.encode(), f"{payload}.{password_hash}".encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        return None
    return user_id


def reset_link(public_url: str, token: str) -> str:
    return f"{public_url.rstrip('/')}/reset?token={token}"


def send_reset_email(host: str, port: int, use_tls: bool, username: str, password: str, sender: str, recipient: str, link: str) -> None:
    message = EmailMessage()
    message["Subject"] = "FUBAR password reset"
    message["From"] = (sender or username).strip()
    message["To"] = recipient
    message.set_content(
        "Use this link to reset your password:\n\n"
        f"{link}\n\n"
        "If you didn't request this, ignore this email."
    )
    with smtplib.SMTP(host, int(port), timeout=20) as smtp:
        if use_tls:
            smtp.starttls()
        if username:
            smtp.login(username, password)
        smtp.send_message(message)
