from flask import Blueprint, jsonify
from ..extensions import db
from ..utils.auth_helper import jwt_required_custom
from datetime import datetime, timedelta
from sqlalchemy import text

tracking_bp = Blueprint("tracking", __name__)


def _get_row(sql, params={}):
    result = db.session.execute(text(sql), params).fetchone()
    return dict(result._mapping) if result else None

def _get_rows(sql, params={}):
    results = db.session.execute(text(sql), params).fetchall()
    return [dict(r._mapping) for r in results]


@tracking_bp.route("/track/<schedule_id>", methods=["GET"])
@jwt_required_custom
def track_boat(schedule_id):
    # Get schedule with boat and route info via raw SQL (avoids UUID mismatch)
    schedule = _get_row(
        """SELECT s.id, s.departure_time, s.arrival_time, s.route_id,
               b.boat_number, r.route_name
        FROM schedules s
        JOIN boats b ON s.boat_id = b.id
        JOIN routes r ON s.route_id = r.id
        WHERE s.id = :sid""",
        {"sid": schedule_id}
    )
    if not schedule:
        return jsonify({"error": "Schedule not found"}), 404

    # Get all stations on this route ordered
    stations = _get_rows(
        """SELECT id, name, order_index
        FROM stations WHERE route_id = :rid
        ORDER BY order_index ASC""",
        {"rid": str(schedule["route_id"])}
    )

    # Parse times
    dep = schedule["departure_time"]
    arr = schedule["arrival_time"]
    dep_str = dep.strftime("%H:%M") if hasattr(dep, "strftime") else str(dep)[:5]
    arr_str = arr.strftime("%H:%M") if hasattr(arr, "strftime") else str(arr)[:5]

    # Current IST time
    now_utc = datetime.utcnow()
    now_ist = now_utc + timedelta(hours=5, minutes=30)
    today = now_ist.date()

    # Build datetime objects for today
    if hasattr(dep, "strftime"):
        dep_dt = datetime.combine(today, dep)
        arr_dt = datetime.combine(today, arr)
    else:
        h, m = map(int, dep_str.split(":"))
        dep_dt = datetime.combine(today, datetime.min.time().replace(hour=h, minute=m))
        h2, m2 = map(int, arr_str.split(":"))
        arr_dt = datetime.combine(today, datetime.min.time().replace(hour=h2, minute=m2))

    total_seconds  = max((arr_dt - dep_dt).total_seconds(), 1)
    elapsed_seconds = (now_ist.replace(tzinfo=None) - dep_dt).total_seconds()

    if elapsed_seconds < 0:
        progress = 0.0
        status = "NOT_STARTED"
        elapsed_min = 0
    elif elapsed_seconds >= total_seconds:
        progress = 1.0
        status = "ARRIVED"
        elapsed_min = int(total_seconds // 60)
    else:
        progress = elapsed_seconds / total_seconds
        status = "IN_TRANSIT"
        elapsed_min = int(elapsed_seconds // 60)

    total_min = int(total_seconds // 60)

    # Which station index is the boat nearest to
    total_st = len(stations)
    if total_st > 1:
        station_float = progress * (total_st - 1)
        current_st_idx = min(int(station_float), total_st - 1)
    else:
        current_st_idx = 0

    return jsonify({
        "schedule_id": schedule_id,
        "route":        schedule["route_name"],
        "boat_number":  schedule["boat_number"],
        "departure_time": dep_str,
        "arrival_time":   arr_str,
        # departure_minutes / arrival_minutes let frontend do its own time math
        "departure_minutes": int(dep_dt.hour * 60 + dep_dt.minute),
        "arrival_minutes":   int(arr_dt.hour * 60 + arr_dt.minute),
        "total_duration_min": total_min,
        "elapsed_min":        elapsed_min,
        "progress_percent":   round(progress * 100, 2),
        "status":             status,
        "current_station_index": current_st_idx,
        "stations": [{"id": str(s["id"]), "name": s["name"], "order_index": s["order_index"]} for s in stations],
        "server_time_ist": now_ist.strftime("%H:%M:%S"),
    }), 200