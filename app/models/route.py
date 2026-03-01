import uuid
from ..extensions import db
from sqlalchemy import text


class Route(db.Model):
    __tablename__ = 'routes'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    route_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)

    # fare column — added via ALTER TABLE in Supabase
    # If it doesn't exist yet, queries will fail — run:
    # ALTER TABLE public.routes ADD COLUMN fare numeric NOT NULL DEFAULT 30;
    fare = db.Column(db.Numeric(10, 2), default=30)

    stations = db.relationship('Station', backref='route', lazy=True, order_by='Station.order_index')

    def to_dict(self):
        fare_val = 30
        try:
            if self.fare is not None:
                fare_val = float(self.fare)
        except Exception:
            pass
        return {
            'id': self.id,
            'route_name': self.route_name,
            'description': self.description,
            'fare': fare_val,
            'stations': [s.to_dict() for s in self.stations]
        }