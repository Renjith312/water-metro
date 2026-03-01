import uuid
from datetime import datetime
from ..extensions import db


class Ticket(db.Model):
    __tablename__ = 'tickets'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    booking_id = db.Column(db.String(36), db.ForeignKey('bookings.id'), nullable=False)
    qr_token = db.Column(db.String(255), unique=True, nullable=False)
    issued_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)
    is_used = db.Column(db.Boolean, default=False)

    def get_status(self):
        if self.is_used:
            return 'USED'
        if self.expires_at:
            # Strip timezone info to make both naive for comparison
            now = datetime.utcnow()
            exp = self.expires_at.replace(tzinfo=None) if self.expires_at.tzinfo else self.expires_at
            if now > exp:
                return 'EXPIRED'
        return 'VALID'

    def to_dict(self):
        return {
            'id': self.id,
            'booking_id': self.booking_id,
            'qr_token': self.qr_token,
            'issued_at': self.issued_at.isoformat() if self.issued_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'is_used': self.is_used,
            'status': self.get_status()
        }