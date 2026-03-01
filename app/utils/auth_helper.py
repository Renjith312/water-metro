from functools import wraps
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from ..models.user import User


def jwt_required_custom(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            verify_jwt_in_request()
        except Exception as e:
            return jsonify({'error': 'Invalid or missing token', 'details': str(e)}), 401
        return f(*args, **kwargs)
    return decorated


def staff_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            verify_jwt_in_request()
            user_id = get_jwt_identity()
            user = User.query.get(user_id)
            if not user or user.role not in ('STAFF', 'ADMIN'):
                return jsonify({'error': 'Staff access required'}), 403
        except Exception as e:
            return jsonify({'error': str(e)}), 401
        return f(*args, **kwargs)
    return decorated


def get_current_user():
    user_id = get_jwt_identity()
    return User.query.get(user_id)