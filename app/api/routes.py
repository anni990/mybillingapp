from flask import Blueprint, jsonify

api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/ping')
def ping():
    return jsonify({'message': 'pong'})

# Register message routes
from . import messages
messages.register_routes(api_bp)
