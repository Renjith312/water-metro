from flask import Blueprint, request, jsonify
from ..extensions import db
from ..utils.auth_helper import jwt_required_custom, get_current_user
from ..utils.qr_helper import generate_qr_token
from datetime import datetime, date, timedelta
from sqlalchemy import text
import uuid

bookings_bp = Blueprint('bookings', __name__)


def _get_row(sql, params={}):
    result = db.session.execute(text(sql), params).fetchone()
    return dict(result._mapping) if result else None


def _get_rows(sql, params={}):
    results = db.session.execute(text(sql), params).fetchall()
    return [dict(r._mapping) for r in results]


def _get_schedule_dict(schedule_id):
    row = _get_row(
        "SELECT s.id, s.departure_time, s.arrival_time, b.boat_number, r.route_name "
        "FROM schedules s JOIN boats b ON s.boat_id = b.id JOIN routes r ON s.route_id = r.id "
        "WHERE s.id = :sid", {'sid': schedule_id}
    )
    if not row:
        return {}
    dep = row['departure_time']
    arr = row['arrival_time']
    return {
        'id': str(row['id']),
        'departure_time': dep.strftime('%H:%M') if hasattr(dep, 'strftime') else str(dep)[:5],
        'arrival_time': arr.strftime('%H:%M') if hasattr(arr, 'strftime') else str(arr)[:5],
        'boat_number': row['boat_number'],
        'route_name': row['route_name'],
    }


@bookings_bp.route('/book', methods=['POST'])
@jwt_required_custom
def create_booking():
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 401

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No JSON body'}), 400

    for field in ['schedule_id', 'travel_date', 'from_station_id', 'to_station_id']:
        if not data.get(field):
            return jsonify({'error': f'{field} is required'}), 400

    ticket_count = int(data.get('ticket_count', 1))
    if not 1 <= ticket_count <= 6:
        return jsonify({'error': 'ticket_count must be 1-6'}), 400

    try:
        travel_date = datetime.strptime(data['travel_date'], '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Invalid date format'}), 400

    # All queries use raw SQL to avoid UUID type mismatch with Supabase
    schedule_row = _get_row(
        "SELECT s.id, s.arrival_time, b.capacity, b.boat_number, r.route_name "
        "FROM schedules s JOIN boats b ON s.boat_id=b.id JOIN routes r ON s.route_id=r.id "
        "WHERE s.id=:sid", {'sid': data['schedule_id']}
    )
    if not schedule_row:
        return jsonify({'error': 'Schedule not found'}), 404

    from_st = _get_row("SELECT id, name FROM stations WHERE id=:sid", {'sid': data['from_station_id']})
    to_st   = _get_row("SELECT id, name FROM stations WHERE id=:sid", {'sid': data['to_station_id']})
    if not from_st or not to_st:
        return jsonify({'error': 'Invalid station ID'}), 404

    booked = db.session.execute(text(
        "SELECT COUNT(*) FROM bookings WHERE schedule_id=:sid AND travel_date=:td AND status!='CANCELLED'"
    ), {'sid': str(schedule_row['id']), 'td': str(travel_date)}).scalar() or 0

    available = (schedule_row['capacity'] or 100) - booked
    if available < ticket_count:
        return jsonify({'error': f'Only {available} seats available'}), 400

    arr = schedule_row['arrival_time']
    if isinstance(arr, str):
        arr = datetime.strptime(arr, '%H:%M:%S').time()
    expires_at = datetime.combine(travel_date, arr) + timedelta(minutes=30)

    uid       = str(user.id)
    sched_id  = str(schedule_row['id'])
    from_id   = str(from_st['id'])
    to_id     = str(to_st['id'])

    result_bookings = []
    try:
        for _ in range(ticket_count):
            bid = str(uuid.uuid4())
            tid = str(uuid.uuid4())
            qr  = generate_qr_token(bid, uid)

            db.session.execute(text(
                "INSERT INTO bookings(id,user_id,schedule_id,travel_date,from_station_id,to_station_id,status,created_at) "
                "VALUES(:id,:uid,:sid,:td,:fid,:tid2,'CONFIRMED',NOW())"
            ), {'id':bid,'uid':uid,'sid':sched_id,'td':str(travel_date),'fid':from_id,'tid2':to_id})

            db.session.execute(text(
                "INSERT INTO tickets(id,booking_id,qr_token,issued_at,expires_at,is_used) "
                "VALUES(:id,:bid,:qr,NOW(),:exp,false)"
            ), {'id':tid,'bid':bid,'qr':qr,'exp':expires_at})

            result_bookings.append({
                'id': bid,
                'travel_date': str(travel_date),
                'status': 'CONFIRMED',
                'from_station': {'id': from_id, 'name': from_st['name']},
                'to_station':   {'id': to_id,   'name': to_st['name']},
                'schedule': {
                    'id': sched_id,
                    'departure_time': None,
                    'arrival_time': arr.strftime('%H:%M') if hasattr(arr,'strftime') else str(arr)[:5],
                    'boat_number': schedule_row['boat_number'],
                    'route_name': schedule_row['route_name'],
                },
                'tickets': [{
                    'id': tid, 'booking_id': bid, 'qr_token': qr,
                    'expires_at': expires_at.isoformat(),
                    'issued_at': datetime.utcnow().isoformat(),
                    'is_used': False, 'status': 'VALID',
                }]
            })

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Booking failed: {str(e)}'}), 500

    # Enrich departure_time after commit
    sched_full = _get_schedule_dict(sched_id)
    for b in result_bookings:
        b['schedule']['departure_time'] = sched_full.get('departure_time')

    return jsonify({
        'message': f'{ticket_count} ticket(s) booked',
        'booking': result_bookings[0],
        'bookings': result_bookings,
        'ticket_count': ticket_count,
    }), 201


@bookings_bp.route('/my-bookings', methods=['GET'])
@jwt_required_custom
def my_bookings():
    user = get_current_user()
    rows = _get_rows(
        "SELECT b.id, b.schedule_id, b.travel_date, b.status, "
        "fs.name as from_name, fs.id as from_id, ts.name as to_name, ts.id as to_id "
        "FROM bookings b "
        "JOIN stations fs ON b.from_station_id=fs.id "
        "JOIN stations ts ON b.to_station_id=ts.id "
        "WHERE b.user_id=:uid AND b.travel_date>=:today AND b.status='CONFIRMED' "
        "ORDER BY b.travel_date ASC",
        {'uid': str(user.id), 'today': str(date.today())}
    )
    now = datetime.utcnow()
    bookings = []
    for row in rows:
        tickets = _get_rows("SELECT * FROM tickets WHERE booking_id=:bid", {'bid': str(row['id'])})
        ticket_list = []
        for t in tickets:
            exp = t['expires_at']
            status = 'USED' if t['is_used'] else ('EXPIRED' if exp and now > exp else 'VALID')
            ticket_list.append({
                'id': str(t['id']), 'booking_id': str(t['booking_id']),
                'qr_token': t['qr_token'],
                'issued_at': t['issued_at'].isoformat() if t['issued_at'] else None,
                'expires_at': exp.isoformat() if exp else None,
                'is_used': t['is_used'], 'status': status,
            })
        bookings.append({
            'id': str(row['id']), 'travel_date': str(row['travel_date']), 'status': row['status'],
            'from_station': {'id': str(row['from_id']), 'name': row['from_name']},
            'to_station':   {'id': str(row['to_id']),   'name': row['to_name']},
            'schedule': _get_schedule_dict(str(row['schedule_id'])),
            'tickets': ticket_list,
        })
    return jsonify({'bookings': bookings}), 200


@bookings_bp.route('/my-history', methods=['GET'])
@jwt_required_custom
def my_history():
    user = get_current_user()
    rows = _get_rows(
        "SELECT b.id, b.schedule_id, b.travel_date, b.status, "
        "fs.name as from_name, fs.id as from_id, ts.name as to_name, ts.id as to_id "
        "FROM bookings b "
        "JOIN stations fs ON b.from_station_id=fs.id "
        "JOIN stations ts ON b.to_station_id=ts.id "
        "WHERE b.user_id=:uid AND (b.travel_date < :today OR b.status IN ('USED','EXPIRED','CANCELLED')) "
        "ORDER BY b.travel_date DESC LIMIT 50",
        {'uid': str(user.id), 'today': str(date.today())}
    )
    return jsonify({'bookings': [{
        'id': str(r['id']), 'travel_date': str(r['travel_date']), 'status': r['status'],
        'from_station': {'id': str(r['from_id']), 'name': r['from_name']},
        'to_station':   {'id': str(r['to_id']),   'name': r['to_name']},
        'schedule': _get_schedule_dict(str(r['schedule_id'])),
    } for r in rows]}), 200


@bookings_bp.route('/cancel-booking/<booking_id>', methods=['POST'])
@jwt_required_custom
def cancel_booking(booking_id):
    user = get_current_user()
    row = _get_row("SELECT id, status FROM bookings WHERE id=:bid AND user_id=:uid",
                   {'bid': booking_id, 'uid': str(user.id)})
    if not row:
        return jsonify({'error': 'Booking not found'}), 404
    if row['status'] != 'CONFIRMED':
        return jsonify({'error': 'Only confirmed bookings can be cancelled'}), 400
    db.session.execute(text("UPDATE bookings SET status='CANCELLED' WHERE id=:bid"), {'bid': booking_id})
    db.session.commit()
    return jsonify({'message': 'Booking cancelled'}), 200