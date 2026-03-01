import uuid
from datetime import datetime,timezone
from ..extensions import db


class Booking(db.Model):
    __tablename__ = 'bookings'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    schedule_id = db.Column(db.String(36), db.ForeignKey('schedules.id'), nullable=False)
    travel_date = db.Column(db.Date, nullable=False)
    from_station_id = db.Column(db.String(36), db.ForeignKey('stations.id'), nullable=False)
    to_station_id = db.Column(db.String(36), db.ForeignKey('stations.id'), nullable=False)
    status = db.Column(db.String(20), default='CONFIRMED')
    created_at = db.Column(
    db.DateTime(timezone=True),
    default=lambda: datetime.now(timezone.utc)
)

    user = db.relationship('User', backref='bookings', lazy=True)
    schedule = db.relationship('Schedule', backref='bookings', lazy=True)
    from_station = db.relationship('Station', foreign_keys=[from_station_id], lazy=True)
    to_station = db.relationship('Station', foreign_keys=[to_station_id], lazy=True)
    tickets = db.relationship('Ticket', backref='booking', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'schedule_id': self.schedule_id,
            'travel_date': self.travel_date.isoformat() if self.travel_date else None,
            'from_station': self.from_station.to_dict() if self.from_station else None,
            'to_station': self.to_station.to_dict() if self.to_station else None,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'schedule': self.schedule.to_dict() if self.schedule else None,
            'tickets': [t.to_dict() for t in self.tickets]
        }