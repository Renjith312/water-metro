from flask import Blueprint, request, jsonify
from ..extensions import db
from ..models.ticket import Ticket
from ..models.booking import Booking
from ..utils.auth_helper import jwt_required_custom, staff_required, get_current_user
from ..utils.qr_helper import verify_qr_token
from datetime import datetime

tickets_bp = Blueprint('tickets', __name__)


@tickets_bp.route('/tickets/<booking_id>', methods=['GET'])
@jwt_required_custom
def get_tickets(booking_id):
    """Get tickets for a booking."""
    user = get_current_user()
    booking = Booking.query.filter_by(id=booking_id, user_id=user.id).first()
    if not booking:
        return jsonify({'error': 'Booking not found'}), 404

    # Auto-update expired tickets
    now = datetime.utcnow()
    for ticket in booking.tickets:
        if not ticket.is_used and now > ticket.expires_at and booking.status == 'CONFIRMED':
            booking.status = 'EXPIRED'
    db.session.commit()

    return jsonify({'tickets': [t.to_dict() for t in booking.tickets]}), 200


@tickets_bp.route('/validate-ticket', methods=['POST'])
@staff_required
def validate_ticket():
    """
    Staff only. POST { qr_token: "..." }
    Verifies ticket and marks as used.
    """
    data = request.get_json()
    qr_token = data.get('qr_token')

    if not qr_token:
        return jsonify({'error': 'qr_token is required'}), 400

    payload = verify_qr_token(qr_token)
    if not payload:
        return jsonify({'valid': False, 'error': 'Invalid or tampered QR code'}), 400

    ticket = Ticket.query.filter_by(qr_token=qr_token).first()
    if not ticket:
        return jsonify({'valid': False, 'error': 'Ticket not found'}), 404

    now = datetime.utcnow()

    if ticket.is_used:
        return jsonify({'valid': False, 'error': 'Ticket already used', 'ticket': ticket.to_dict()}), 400

    if now > ticket.expires_at:
        return jsonify({'valid': False, 'error': 'Ticket expired', 'ticket': ticket.to_dict()}), 400

    ticket.is_used = True
    booking = ticket.booking
    if booking:
        booking.status = 'USED'
    db.session.commit()

    return jsonify({
        'valid': True,
        'message': 'Ticket validated successfully',
        'ticket': ticket.to_dict(),
        'booking': booking.to_dict() if booking else None
    }), 200