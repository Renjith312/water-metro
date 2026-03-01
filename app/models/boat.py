import uuid
from ..extensions import db


class Boat(db.Model):
    __tablename__ = 'boats'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    boat_number = db.Column(db.String(50), unique=True, nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='ACTIVE')
    # NO created_at — column does not exist in database

    def to_dict(self):
        return {
            'id': self.id,
            'boat_number': self.boat_number,
            'capacity': self.capacity,
            'status': self.status
        }