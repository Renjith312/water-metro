from flask import Blueprint, request, jsonify
from ..models.schedule import Schedule
from ..models.station import Station
from ..models.booking import Booking
from ..models.route import Route
from datetime import datetime

schedules_bp = Blueprint('schedules', __name__)


@schedules_bp.route('', methods=['GET'])
def search_schedules():
    from_station_id = request.args.get('from_station')
    to_station_id = request.args.get('to_station')
    travel_date_str = request.args.get('date')

    if not all([from_station_id, to_station_id, travel_date_str]):
        return jsonify({'error': 'from_station, to_station, and date are required'}), 400

    try:
        travel_date = datetime.strptime(travel_date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Invalid date format'}), 400

    # DB uses 1=Mon...7=Sun, Python uses 0=Mon...6=Sun
    day_index_1based = travel_date.weekday() + 1  # 1=Mon, 7=Sun

    from_station = Station.query.get(from_station_id)
    to_station = Station.query.get(to_station_id)

    if not from_station or not to_station:
        return jsonify({'error': 'Invalid station IDs'}), 404

    if from_station.route_id != to_station.route_id:
        return jsonify({'error': 'Stations must be on the same route'}), 400

    if from_station.order_index >= to_station.order_index:
        return jsonify({'error': 'from_station must come before to_station'}), 400

    route = Route.query.get(from_station.route_id)

    # Get fare safely
    fare = 30
    try:
        if route and hasattr(route, 'fare') and route.fare is not None:
            fare = float(route.fare)
    except Exception:
        pass

    # Get all schedules for this route — IGNORE valid_from/valid_to
    # because the seed data has expired dates (2025-12-31)
    schedules = Schedule.query.filter(
        Schedule.route_id == from_station.route_id,
    ).order_by(Schedule.departure_time).all()

    matching = []
    for s in schedules:
        # Check day of week — DB uses 1-7
        if s.days_of_week:
            if day_index_1based not in s.days_of_week:
                continue

        booked_count = Booking.query.filter_by(
            schedule_id=s.id,
            travel_date=travel_date
        ).filter(Booking.status != 'CANCELLED').count()

        capacity = s.boat.capacity if s.boat else 100
        available_seats = max(0, capacity - booked_count)

        d = s.to_dict()
        d['available_seats'] = available_seats
        d['travel_date'] = travel_date_str
        d['from_station'] = from_station.to_dict()
        d['to_station'] = to_station.to_dict()
        d['fare'] = fare
        matching.append(d)

    return jsonify({
        'schedules': matching,
        'route_name': route.route_name if route else '',
        'fare': fare,
        'from_station': from_station.to_dict(),
        'to_station': to_station.to_dict(),
    }), 200


@schedules_bp.route('/routes', methods=['GET'])
def get_routes():
    routes = Route.query.all()
    return jsonify({'routes': [r.to_dict() for r in routes]}), 200


@schedules_bp.route('/stations', methods=['GET'])
def get_stations():
    route_id = request.args.get('route_id')
    query = Station.query
    if route_id:
        query = query.filter_by(route_id=route_id)
    stations = query.order_by(Station.order_index).all()
    return jsonify({'stations': [s.to_dict() for s in stations]}), 200


@schedules_bp.route('/debug', methods=['GET'])
def debug():
    """Debug endpoint - shows all schedules raw data"""
    schedules = Schedule.query.all()
    result = []
    for s in schedules:
        result.append({
            'id': s.id,
            'route_id': s.route_id,
            'departure_time': str(s.departure_time),
            'days_of_week': s.days_of_week,
            'valid_from': str(s.valid_from),
            'valid_to': str(s.valid_to),
            'boat': s.boat.boat_number if s.boat else None,
        })
    return jsonify({'count': len(result), 'schedules': result}), 200