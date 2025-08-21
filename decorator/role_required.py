from functools import wraps
from flask_jwt_extended import verify_jwt_in_request, get_jwt
from flask import jsonify
from flask_jwt_extended.exceptions import NoAuthorizationError, InvalidHeaderError

def role_required(roles):
    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            try:
                verify_jwt_in_request()
            except Exception:
                return jsonify({"msg": "Token de autorización faltante o inválido"}), 401
            claims = get_jwt()
            if claims.get("role") not in roles:
                return jsonify({"msg": "Acceso denegado, se requiere rol(es): " + str(roles)}), 403
            return fn(*args, **kwargs)
        return decorator
    return wrapper
