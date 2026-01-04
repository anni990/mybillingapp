from flask import Blueprint, jsonify
from ..extensions import csrf

api_bp = Blueprint('api', __name__, url_prefix='/api')

# Exempt API routes from CSRF protection for internal calls
csrf.exempt(api_bp)

@api_bp.route('/ping')
def ping():
    return jsonify({'message': 'pong'})

# Register message routes
from . import messages
messages.register_routes(api_bp)
