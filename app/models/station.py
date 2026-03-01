import uuid
from ..extensions import db


class Station(db.Model):
    __tablename__ = 'stations'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(100), nullable=False)
    route_id = db.Column(db.String(36), db.ForeignKey('routes.id', ondelete='CASCADE'))
    order_index = db.Column(db.Integer, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'route_id': self.route_id,
            'order_index': self.order_index
        }