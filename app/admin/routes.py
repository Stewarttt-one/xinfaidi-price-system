from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from app import db
from app.models import User

admin_bp = Blueprint('admin', __name__)


def admin_required(func):
    from functools import wraps
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            return jsonify({'error': '需要管理员权限'}), 403
        return func(*args, **kwargs)
    return wrapper


@admin_bp.route('/users_page')
@login_required
@admin_required
def users_page():
    return render_template('admin/users.html')


@admin_bp.route('/api/users', methods=['GET'])
@login_required
@admin_required
def get_users():
    # 获取分页参数
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    username = request.args.get('username', '', type=str)

    query = User.query
    if username:
        query = query.filter(User.username.like('%{}%'.format(username)))

    # 分页查询
    pagination = query.order_by(User.id.asc()).paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'success': True,
        'data': [{
            'id': u.id,
            'username': u.username,
            'role': u.role,
            'create_time': u.create_time.strftime('%Y-%m-%d %H:%M')
        } for u in pagination.items],
        'total': pagination.total,
        'page': page,
        'pages': pagination.pages,
        'per_page': per_page
    })


@admin_bp.route('/api/users/<int:id>', methods=['GET'])
@login_required
@admin_required
def get_user(id):
    user = User.query.get_or_404(id)
    return jsonify({
        'success': True,
        'data': {
            'id': user.id,
            'username': user.username,
            'role': user.role
        }
    })


@admin_bp.route('/api/users', methods=['POST'])
@login_required
@admin_required
def add_user():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    role = data.get('role', 'user')

    if not username or not password:
        return jsonify({'success': False, 'error': '用户名和密码不能为空'}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({'success': False, 'error': '用户名已存在'}), 400

    user = User(username=username, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    return jsonify({'success': True, 'message': '添加成功'})


@admin_bp.route('/api/users/<int:id>', methods=['PUT'])
@login_required
@admin_required
def update_user(id):
    user = User.query.get_or_404(id)

    data = request.get_json()
    new_username = data.get('username')
    new_role = data.get('role')

    if new_username and new_username != user.username:
        existing_user = User.query.filter_by(username=new_username).first()
        if existing_user:
            return jsonify({'success': False, 'error': '用户名已存在'}), 400
        user.username = new_username

    if new_role:
        user.role = new_role

    db.session.commit()

    return jsonify({'success': True, 'message': '更新成功'})


@admin_bp.route('/api/users/<int:id>', methods=['DELETE'])
@login_required
@admin_required
def delete_user(id):
    user = User.query.get_or_404(id)

    if user.id == current_user.id:
        return jsonify({'success': False, 'error': '不能删除自己'}), 400

    db.session.delete(user)
    db.session.commit()

    return jsonify({'success': True, 'message': '删除成功'})