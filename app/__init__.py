from flask import Flask
from .config import Config
from .extensions import db, jwt
from flask_cors import CORS


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Init extensions
    db.init_app(app)
    jwt.init_app(app)

    # Allow all origins explicitly
    CORS(app, resources={r"/*": {
        "origins": [
            "http://localhost:8081",
            "http://localhost:19006",
            "http://127.0.0.1:8081",
            "exp://192.168.29.104:8081",
            "*"
        ],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }})

    # Register blueprints
    from .routes.auth import auth_bp
    from .routes.schedules import schedules_bp
    from .routes.bookings import bookings_bp
    from .routes.tickets import tickets_bp
    from .routes.tracking import tracking_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(schedules_bp, url_prefix='/schedules')
    app.register_blueprint(bookings_bp)
    app.register_blueprint(tickets_bp)
    app.register_blueprint(tracking_bp)

    with app.app_context():
        db.create_all()

    return app