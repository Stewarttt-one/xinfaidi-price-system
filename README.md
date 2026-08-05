新发地菜价分析系统

一、环境要求
Python 3.7.4
MySQL 5.7+

二、安装步骤
1. 创建数据库
CREATE DATABASE xinfaidi_db CHARACTER SET utf8mb4;
2. 配置数据库
修改 config.py 中的数据库密码：
MYSQL_PASSWORD = '密码'
3. 创建虚拟环境并安装依赖
bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
4. 初始化数据库
python run.py

三、启动项目
venv\Scripts\activate
python run.py
访问：http://localhost:5000/auth/login

四、测试账号
角色	        用户名	 密码
管理员	admin	123456
普通用户	user01	111111