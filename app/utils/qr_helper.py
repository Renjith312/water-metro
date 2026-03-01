import hmac
import hashlib
import secrets
import os
import json
import base64


def generate_qr_token(booking_id: str, ticket_id: str) -> str:
    """Generate a secure signed QR token."""
    secret = os.environ.get('JWT_SECRET_KEY', 'fallback')
    payload = json.dumps({'booking_id': booking_id, 'ticket_id': ticket_id, 'nonce': secrets.token_hex(8)})
    sig = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    token_data = f"{payload}|{sig}"
    return base64.urlsafe_b64encode(token_data.encode()).decode()


def verify_qr_token(token: str) -> dict | None:
    """Verify and decode a QR token. Returns payload dict or None."""
    try:
        secret = os.environ.get('JWT_SECRET_KEY', 'fallback')
        decoded = base64.urlsafe_b64decode(token.encode()).decode()
        payload_str, sig = decoded.rsplit('|', 1)
        expected_sig = hmac.new(secret.encode(), payload_str.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected_sig):
            return None
        return json.loads(payload_str)
    except Exception:
        return None