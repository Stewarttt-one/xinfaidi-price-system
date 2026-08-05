from flask import Blueprint, render_template, redirect, url_for, flash, request,jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models import User

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            flash('用户名和密码不能为空')
            return render_template('login.html')

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user, remember=True)
            return redirect(url_for('main.index'))
        else:
            flash('用户名或密码错误')

    return render_template('login.html')


@auth_bp.route('/change_password', methods=['POST'])
@login_required
def change_password():
    """修改当前用户密码"""
    data = request.get_json()
    old_password = data.get('old_password')
    new_password = data.get('new_password')

    if not old_password or not new_password:
        return jsonify({'success': False, 'error': '原密码和新密码不能为空'}), 400

    if len(new_password) < 6:
        return jsonify({'success': False, 'error': '新密码长度不能少于6位'}), 400

    user = User.query.get(current_user.id)

    if not user.check_password(old_password):
        return jsonify({'success': False, 'error': '原密码错误'}), 400

    user.set_password(new_password)
    db.session.commit()

    return jsonify({'success': True, 'message': '密码修改成功'})


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
