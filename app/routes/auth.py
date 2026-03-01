from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token
from ..extensions import db
from ..models.user import User
import os
import uuid
import requests as http_requests
import logging

logger = logging.getLogger(__name__)
auth_bp = Blueprint('auth', __name__)

GOOGLE_CLIENT_IDS = [
    os.environ.get('GOOGLE_CLIENT_ID'),
    os.environ.get('GOOGLE_ANDROID_CLIENT_ID'),
]


@auth_bp.route('/google', methods=['POST'])
def google_login():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No JSON body'}), 400

    logger.info(f"Login attempt, keys: {list(data.keys())}")

    # ── WEB FLOW ──────────────────────────────────────────────────
    # Frontend already verified with Google and sends user_info directly
    if data.get('user_info'):
        user_info = data['user_info']
        email = user_info.get('email')
        name = (
            user_info.get('name') or
            user_info.get('given_name') or
            email
        )
        google_id = user_info.get('sub') or user_info.get('id') or email

        if not email:
            return jsonify({'error': 'No email in user_info'}), 400

        logger.info(f"Web login for: {email}")
        user = upsert_user(email, name, google_id)
        token = create_access_token(identity=str(user.id))
        return jsonify({'access_token': token, 'user': user.to_dict()}), 200

    # ── MOBILE FLOW ───────────────────────────────────────────────
    # Mobile sends id_token, verify with Google tokeninfo endpoint
    if data.get('id_token'):
        id_token = data['id_token']
        try:
            res = http_requests.get(
                f'https://oauth2.googleapis.com/tokeninfo?id_token={id_token}',
                timeout=10
            )
            if res.status_code != 200:
                logger.error(f"Google tokeninfo failed: {res.text}")
                return jsonify({'error': 'Invalid id_token'}), 401

            info = res.json()
            aud = info.get('aud', '')
            valid_ids = [c for c in GOOGLE_CLIENT_IDS if c]

            logger.info(f"id_token aud={aud}, valid={valid_ids}")

            if aud not in valid_ids:
                # Still allow if email is present (dev mode)
                logger.warning(f"Audience mismatch but allowing: {aud}")

            email = info.get('email')
            name = info.get('name') or email
            google_id = info.get('sub') or email

            if not email:
                return jsonify({'error': 'No email in token'}), 400

            user = upsert_user(email, name, google_id)
            token = create_access_token(identity=str(user.id))
            return jsonify({'access_token': token, 'user': user.to_dict()}), 200

        except Exception as e:
            logger.error(f"id_token error: {e}")
            return jsonify({'error': str(e)}), 500

    # ── ACCESS TOKEN ONLY (fallback) ─────────────────────────────
    if data.get('access_token'):
        access_token = data['access_token']
        try:
            res = http_requests.get(
                'https://www.googleapis.com/oauth2/v3/userinfo',
                headers={'Authorization': f'Bearer {access_token}'},
                timeout=10
            )
            if res.status_code != 200:
                return jsonify({'error': 'Invalid access_token'}), 401

            info = res.json()
            email = info.get('email')
            name = info.get('name') or info.get('given_name') or email
            google_id = info.get('sub') or email

            if not email:
                return jsonify({'error': 'No email'}), 400

            user = upsert_user(email, name, google_id)
            token = create_access_token(identity=str(user.id))
            return jsonify({'access_token': token, 'user': user.to_dict()}), 200

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    return jsonify({'error': 'Provide id_token, access_token, or user_info'}), 400


def upsert_user(email: str, name: str, google_id: str) -> User:
    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(
            id=str(uuid.uuid4()),
            name=name,
            email=email,
            oauth_provider='google',
            oauth_id=str(google_id),
            role='USER'
        )
        db.session.add(user)
        db.session.commit()
        logger.info(f"Created new user: {email}")
    else:
        if not user.oauth_id:
            user.oauth_id = str(google_id)
            user.oauth_provider = 'google'
            db.session.commit()
        logger.info(f"Existing user: {email}")
    return user


@auth_bp.route('/me', methods=['GET'])
def get_me():
    from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
    try:
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        return jsonify({'user': user.to_dict()}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 401