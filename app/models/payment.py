import uuid
from datetime import datetime
from ..extensions import db


class Payment(db.Model):
    __tablename__ = 'payments'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    booking_id = db.Column(db.String(36), db.ForeignKey('bookings.id'))
    amount = db.Column(db.Numeric(10, 2))
    status = db.Column(db.String(20), default='SUCCESS')
    payment_method = db.Column(db.String(50))
    paid_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'booking_id': self.booking_id,
            'amount': float(self.amount) if self.amount else 0,
            'status': self.status,
            'payment_method': self.payment_method,
            'paid_at': self.paid_at.isoformat() if self.paid_at else None
        }