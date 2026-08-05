# -*- coding: utf-8 -*-
import requests
import json
from datetime import date, timedelta
from app import db
from app.models import PriceHistory, VegetablePrice


class AIService:
    def __init__(self):
        self.api_key = "sk-6343e698a9fb47f78e5f502db18b6faf"
        self.api_url = "https://api.deepseek.com/v1/chat/completions"

    def get_price_context(self):
        """获取当前价格数据作为AI的上下文"""
        today = date.today()

        # 获取今日价格TOP20
        today_prices = VegetablePrice.query.filter_by(source_date=today).order_by(VegetablePrice.price).limit(20).all()

        context = "=== 今日蔬菜价格数据 ===\n"
        for p in today_prices:
            context += "{}: {:.2f}元/斤\n".format(p.name, p.price)

        # 获取涨幅排行TOP5
        start_date = today - timedelta(days=20)
        vegetables = VegetablePrice.query.filter_by(source_date=today).all()
        rankings = []
        for veg in vegetables[:30]:
            histories = PriceHistory.query.filter(
                PriceHistory.prod_name == veg.name,
                PriceHistory.record_date >= start_date,
                PriceHistory.price > 0
            ).all()
            if histories:
                avg_20d = sum(h.price for h in histories) / len(histories)
                if avg_20d > 0:
                    change_rate = (veg.price - avg_20d) / avg_20d * 100
                    rankings.append((veg.name, change_rate))

        rankings.sort(key=lambda x: x[1], reverse=True)
        context += "\n=== 近20日涨幅排行 ===\n"
        for name, rate in rankings[:5]:
            context += "{}: +{:.2f}%\n".format(name, rate)

        context += "\n=== 近20日跌幅排行 ===\n"
        for name, rate in rankings[-5:]:
            context += "{}: {:.2f}%\n".format(name, rate)

        return context

    def chat(self, user_question):
        """智能问答 - 使用大模型"""

        # 获取价格上下文
        price_context = self.get_price_context()

        # 系统提示词
        system_prompt = """你是一个专业的蔬菜价格分析助手。用户会问你各种关于蔬菜价格的问题。
请根据提供的价格数据回答问题。如果数据中找不到答案，请诚实告知用户。

规则：
1. 回答要简洁、准确、有用
2. 涉及价格时保留两位小数
3. 可以回答对比、趋势、预测等问题
4. 如果用户问的是历史数据（如"昨天多少钱"），但数据中只有今天的，请说明
5. 回答要友好"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "以下是当前的价格数据：\n\n" + price_context + "\n\n用户问题：" + user_question}
        ]

        headers = {
            "Authorization": "Bearer " + self.api_key,
            "Content-Type": "application/json"
        }

        data = {
            "model": "deepseek-chat",
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 500
        }

        try:
            response = requests.post(self.api_url, headers=headers, json=data, timeout=30)
            result = response.json()

            if "choices" in result and len(result["choices"]) > 0:
                return result["choices"][0]["message"]["content"]
            else:
                return "AI服务暂时不可用，请稍后再试"

        except Exception as e:
            return "AI服务出错：{}".format(str(e))