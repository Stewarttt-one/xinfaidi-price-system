# -*- coding: utf-8 -*-
import requests
import time
import random
import pandas as pd
from datetime import datetime, timedelta, date
from app import db


# ==================== 数据采集函数 ====================

def get_latest_date_from_db():
    """获取数据库中最新的数据日期"""
    from app.models import PriceHistory
    latest = PriceHistory.query.order_by(PriceHistory.record_date.desc()).first()
    if latest:
        return latest.record_date
    return None


def fetch_one_day_complete(target_date, max_retries=3):
    """完整采集某一天的所有数据"""
    api_url = "http://www.xinfadi.com.cn/getPriceData.html"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "http://www.xinfadi.com.cn/priceDetail.html",
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
    }

    date_str = target_date.strftime('%Y/%m/%d')
    all_data = []
    current_page = 1

    while True:
        retry_count = 0
        success = False
        data_list = []

        while retry_count < max_retries and not success:
            data = {
                "current": current_page,
                "limit": 20,
                "pubDateStartTime": date_str,
                "pubDateEndTime": date_str,
                "prodPcatid": "",
                "prodCatid": "",
                "prodName": ""
            }

            try:
                time.sleep(random.uniform(0.3, 0.6))
                response = requests.post(api_url, headers=headers, data=data, timeout=30)

                if response.status_code != 200:
                    retry_count += 1
                    print("    第{}页 HTTP {}, 重试 {}/{}".format(current_page, response.status_code, retry_count, max_retries))
                    time.sleep(1)
                    continue

                result = response.json()
                data_list = result.get("list", [])
                success = True

            except requests.exceptions.Timeout:
                retry_count += 1
                print("    第{}页超时, 重试 {}/{}".format(current_page, retry_count, max_retries))
                time.sleep(2)
            except Exception as e:
                retry_count += 1
                print("    第{}页错误: {}, 重试 {}/{}".format(current_page, str(e), retry_count, max_retries))
                time.sleep(2)

        if not success:
            print("    第{}页失败，停止采集".format(current_page))
            break

        if not data_list:
            print("    第{}页无数据，采集完成".format(current_page))
            break

        all_data.extend(data_list)
        print("    第{}页: {} 条".format(current_page, len(data_list)))

        if len(data_list) < 20:
            print("    第{}页数据不足20条，采集完成".format(current_page))
            break

        current_page += 1

    return all_data


def save_one_day_to_db(data_list, target_date):
    """保存一天的数据到数据库"""
    from app.models import PriceHistory

    deleted = PriceHistory.query.filter_by(record_date=target_date).delete()
    if deleted > 0:
        print("  删除旧数据 {} 条".format(deleted))

    saved = 0
    for item in data_list:
        try:
            name = item.get('prodName', '').strip()
            if not name:
                continue

            prod_pcat = item.get('prodPcat', '')
            prod_cat = item.get('prodCat', '')
            if prod_pcat != '蔬菜' and prod_cat != '蔬菜':
                continue

            price = float(item.get('avgPrice', 0)) if item.get('avgPrice') else 0
            if price <= 0:
                continue

            min_price = float(item.get('lowPrice', 0)) if item.get('lowPrice') else 0
            max_price = float(item.get('highPrice', 0)) if item.get('highPrice') else 0
            place = item.get('place', '')
            unit = item.get('unitInfo', '斤')

            history = PriceHistory(
                prod_name=name,
                price=price,
                record_date=target_date,
                min_price=min_price,
                max_price=max_price,
                place=place,
                unit=unit
            )
            db.session.add(history)
            saved += 1

        except Exception as e:
            print("  保存失败: {}".format(str(e)))
            continue

    db.session.commit()
    return saved


def sync_missing_data():
    """同步缺失的数据"""
    latest_date = get_latest_date_from_db()
    today_date = date.today()

    if not latest_date:
        print("数据库中没有数据，请先运行全量同步脚本")
        return {"success": False, "message": "数据库中没有数据，请先全量同步", "new_count": 0}

    if latest_date >= today_date:
        print("数据已是最新，无需同步")
        return {"success": True, "message": "数据已是最新，无需同步", "new_count": 0}

    start_date = latest_date + timedelta(days=1)

    print("=" * 60)
    print("数据同步开始")
    print("数据库最新日期: {}".format(latest_date))
    print("需要同步日期: {} 至 {}".format(start_date, today_date))
    print("=" * 60)

    current_date = start_date
    total_saved = 0
    day_count = 0
    total_days = (today_date - start_date).days + 1

    while current_date <= today_date:       #逐日循环采集
        day_count += 1
        print("\n[{}/{}] 正在同步 {}...".format(day_count, total_days, current_date))

        raw_data = fetch_one_day_complete(current_date)

        if raw_data:
            saved = save_one_day_to_db(raw_data, current_date)
            total_saved += saved
            print("  保存 {} 条新数据".format(saved))
        else:
            print("  无数据")

        current_date += timedelta(days=1)
        time.sleep(0.5)

    update_today_prices_with_pandas()

    print("\n" + "=" * 60)
    print("数据同步完成！")
    print("同步日期范围: {} 至 {}".format(start_date, today_date))
    print("共处理 {} 天，新增 {} 条数据".format(total_days, total_saved))
    print("=" * 60)

    return {"success": True, "message": "同步完成！新增 {} 条数据".format(total_saved), "new_count": total_saved}


# ==================== 核心函数 ====================

def get_rankings_with_pandas(limit=6):
    """使用 pandas 计算涨幅/跌幅排行"""
    from app.models import PriceHistory
    from sqlalchemy import func

    today = date.today()
    start_date = today - timedelta(days=20)

    # 获取每种蔬菜的最新价格
    subquery = db.session.query(
        PriceHistory.prod_name,
        func.max(PriceHistory.record_date).label('max_date')
    ).group_by(PriceHistory.prod_name).subquery()

    latest_prices = db.session.query(
        PriceHistory.prod_name,
        PriceHistory.price
    ).join(
        subquery,
        (PriceHistory.prod_name == subquery.c.prod_name) &
        (PriceHistory.record_date == subquery.c.max_date)
    ).all()

    # 获取20日均价
    avg_query = db.session.query(
        PriceHistory.prod_name,
        func.avg(PriceHistory.price).label('avg_price')
    ).filter(
        PriceHistory.record_date >= start_date,
        PriceHistory.price > 0
    ).group_by(PriceHistory.prod_name).all()

    if not latest_prices or not avg_query:
        return [], []

    # 转换为 DataFrame
    df_latest = pd.DataFrame(latest_prices, columns=['name', 'current_price'])
    df_avg = pd.DataFrame(avg_query, columns=['name', 'avg_price_20d'])

    # 合并数据
    df = pd.merge(df_latest, df_avg, on='name', how='inner')

    # 计算涨幅
    df['change_rate'] = ((df['current_price'] - df['avg_price_20d']) / df['avg_price_20d'] * 100).round(2)

    # 涨幅排行
    top_increase = df.nlargest(limit, 'change_rate')[['name', 'current_price', 'avg_price_20d', 'change_rate']].to_dict('records')

    # 跌幅排行
    top_decrease = df.nsmallest(limit, 'change_rate')[['name', 'current_price', 'avg_price_20d', 'change_rate']].to_dict('records')

    # 格式化跌幅值
    for item in top_decrease:
        item['change_rate'] = abs(item['change_rate'])

    return top_increase, top_decrease


def update_today_prices_with_pandas():
    from app.models import VegetablePrice, PriceHistory
    from sqlalchemy import func

    print("正在使用 pandas 更新今日价格表...")

    # 获取每种蔬菜的最新价格
    subquery = db.session.query(
        PriceHistory.prod_name,
        func.max(PriceHistory.record_date).label('max_date')
    ).group_by(PriceHistory.prod_name).subquery()

    latest_prices = db.session.query(
        PriceHistory.prod_name,
        PriceHistory.price,
        PriceHistory.min_price,
        PriceHistory.max_price,
        PriceHistory.record_date
    ).join(
        subquery,
        (PriceHistory.prod_name == subquery.c.prod_name) &
        (PriceHistory.record_date == subquery.c.max_date)
    ).all()

    if not latest_prices:
        return

    # 转换为 DataFrame
    df = pd.DataFrame(latest_prices, columns=['name', 'price', 'min_price', 'max_price', 'record_date'])

    # 批量更新数据库
    for _, row in df.iterrows():
        name = row['name']
        current_price = row['price']
        current_min = row['min_price']
        current_max = row['max_price']
        current_date = row['record_date']

        yesterday = current_date - timedelta(days=1)
        yesterday_record = PriceHistory.query.filter_by(
            prod_name=name,
            record_date=yesterday
        ).first()
        yesterday_price = yesterday_record.price if yesterday_record else None

        existing = VegetablePrice.query.filter_by(
            name=name,
            source_date=current_date
        ).first()

        if existing:
            existing.price = current_price
            existing.min_price = current_min
            existing.max_price = current_max
            existing.yesterday_price = yesterday_price
            existing.update_time = datetime.now()
        else:
            veg_price = VegetablePrice(
                name=name,
                category="蔬菜",
                price=current_price,
                min_price=current_min,
                max_price=current_max,
                yesterday_price=yesterday_price,
                source_date=current_date,
                update_time=datetime.now()
            )
            db.session.add(veg_price)

    # 计算并更新均价
    for name in df['name'].unique():
        avg_7d = calculate_avg_price_with_pandas(name, 7)
        avg_20d = calculate_avg_price_with_pandas(name, 20)

        veg = VegetablePrice.query.filter_by(
            name=name,
            source_date=df[df['name'] == name]['record_date'].iloc[0]
        ).first()
        if veg:
            veg.avg_price_7d = avg_7d
            veg.avg_price_20d = avg_20d

    db.session.commit()
    print("今日价格表更新完成（pandas版）")


def calculate_avg_price_with_pandas(vegetable_name, days):
    """使用 pandas 计算指定蔬菜的N日均价"""
    from app.models import PriceHistory

    start_date = date.today() - timedelta(days=days)

    query = db.session.query(
        PriceHistory.price
    ).filter(
        PriceHistory.prod_name == vegetable_name,
        PriceHistory.record_date >= start_date,
        PriceHistory.price > 0
    ).all()

    if not query:
        return None

    df = pd.DataFrame(query, columns=['price'])
    return round(df['price'].mean(), 2)


def get_price_trend_with_pandas(vegetable_name, days=30):
    from app.models import PriceHistory
    import pandas as pd

    start_date = date.today() - timedelta(days=days)

    query = db.session.query(
        PriceHistory.record_date,
        PriceHistory.price,
        PriceHistory.min_price,
        PriceHistory.max_price
    ).filter(
        PriceHistory.prod_name == vegetable_name,
        PriceHistory.record_date >= start_date
    ).order_by(PriceHistory.record_date.asc()).all()

    if not query:
        return []

    df = pd.DataFrame(query, columns=['date', 'price', 'min_price', 'max_price'])

    df['date'] = pd.to_datetime(df['date'])
    df['date'] = df['date'].dt.strftime('%Y-%m-%d')

    return df.to_dict('records')


# ==================== 兼容原有接口的函数 ====================

def update_today_prices():
    """更新今日价格表"""
    update_today_prices_with_pandas()


def get_top_rankings(limit=6, is_increase=True):
    """获取涨幅/跌幅排行"""
    increase, decrease = get_rankings_with_pandas(limit)
    return increase if is_increase else decrease


def get_vegetable_price_history(vegetable_name, days=30):
    """获取蔬菜历史价格"""
    return get_price_trend_with_pandas(vegetable_name, days)


def calculate_avg_price(vegetable_name, days):
    """计算指定蔬菜的N日均价"""
    return calculate_avg_price_with_pandas(vegetable_name, days)


def calculate_price_change_rate(current_price, yesterday_price):
    """计算价格涨跌幅"""
    if not yesterday_price or yesterday_price == 0:
        return 0
    return round((current_price - yesterday_price) / yesterday_price * 100, 2)


def get_total_count():
    """获取总数据量"""
    from app.models import VegetablePrice
    today = date.today()
    return VegetablePrice.query.filter_by(source_date=today).count()


def get_avg_price_today():
    """获取今日均价"""
    from app.models import VegetablePrice
    today = date.today()
    prices = VegetablePrice.query.filter_by(source_date=today).all()
    if not prices:
        return 0
    total = sum(p.price for p in prices)
    return round(total / len(prices), 2)