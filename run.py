import sys
import io

# 解决编码问题（Python 3 方式）
import importlib

importlib.reload(sys)

from app import create_app, db
from app.models import User, VegetablePrice, PriceHistory, OperationLog

app = create_app()


@app.shell_context_processor
def make_shell_context():
    return {
        'db': db,
        'User': User,
        'VegetablePrice': VegetablePrice,
        'PriceHistory': PriceHistory,
        'OperationLog': OperationLog
    }


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print("=" * 50)
        print("用户账号: user01 / 111111")
        print("管理员账号: admin / 123456")
        print("=" * 50)

    app.run(host='0.0.0.0', port=5000, debug=True)