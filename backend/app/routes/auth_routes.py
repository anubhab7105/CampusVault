from flask import Blueprint, request, jsonify
from app.services.auth_service import create_user

bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@bp.route('/signup', methods=['POST'])
def signup():
    data = request.get_json() or {}
    required = ['name', 'email', 'password', 'role', 'college_id']
    for r in required:
        if r not in data:
            return jsonify({'error': f'Missing field: {r}'}), 400

    try:
        res = create_user(
            name=data['name'].strip(),
            email=data['email'].strip(),
            password=data['password'],
            college_id=data['college_id'].strip(),
            role=data['role'].strip()
        )
    except Exception as e:
        return jsonify({'error': 'Failed to create user', 'details': str(e)}), 400

    user = res['user']
    token = res['token']
    return jsonify({
        'token': token,
        'user': {
            'unique_id': getattr(user, 'unique_id', getattr(user, 'uniqueId', None) or getattr(user, 'id', None)),
            'name': getattr(user, 'name', None),
            'email': getattr(user, 'email', None),
            'role': getattr(user, 'role', None)
        },
        'siteid': res.get('siteid')
    }), 201
