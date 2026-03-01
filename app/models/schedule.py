import uuid
from ..extensions import db
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy import Integer


class Schedule(db.Model):
    __tablename__ = 'schedules'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    route_id = db.Column(db.String(36), db.ForeignKey('routes.id'), nullable=False)
    boat_id = db.Column(db.String(36), db.ForeignKey('boats.id'), nullable=False)
    departure_time = db.Column(db.Time, nullable=False)
    arrival_time = db.Column(db.Time, nullable=False)
    days_of_week = db.Column(ARRAY(Integer))
    valid_from = db.Column(db.Date)
    valid_to = db.Column(db.Date)

    route = db.relationship('Route', backref='schedules', lazy=True)
    boat = db.relationship('Boat', backref='schedules', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'route_id': self.route_id,
            'route_name': self.route.route_name if self.route else None,
            'boat_id': self.boat_id,
            'boat_number': self.boat.boat_number if self.boat else None,
            'boat_capacity': self.boat.capacity if self.boat else None,
            'departure_time': self.departure_time.strftime('%H:%M') if self.departure_time else None,
            'arrival_time': self.arrival_time.strftime('%H:%M') if self.arrival_time else None,
            'days_of_week': self.days_of_week,
            'valid_from': self.valid_from.isoformat() if self.valid_from else None,
            'valid_to': self.valid_to.isoformat() if self.valid_to else None,
            'stations': [s.to_dict() for s in self.route.stations] if self.route else []
        }