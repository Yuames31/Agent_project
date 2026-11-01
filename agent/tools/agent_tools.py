import os
import random
import requests
from datetime import datetime
from langchain_core.tools import tool
from rag.rag_service import RagSummarizeService
from utils.config_handler import agent_conf, weather_conf
from utils.path_tool import get_abs_path
from utils.logger_handler import logger

rag = RagSummarizeService()
# 常用城市 -> 和风天气 LocationID（采用内置映射）
CITY_IDS = {
    "北京": "101010100", "上海": "101020100", "天津": "101030100", "重庆": "101040100",
    "广州": "101280101", "深圳": "101280601", "东莞": "101281601", "佛山": "101280800",
    "珠海": "101280701", "杭州": "101210101", "成都": "101270101", "武汉": "101200101",
    "南京": "101190101", "苏州": "101190401", "长沙": "101250101", "西安": "101110101",
    "郑州": "101180101", "青岛": "101120201", "厦门": "101230201", "香港": "101320101",
}


def normalize_city_name(city: str) -> str:
    """归一化城市名，'广州市' -> '广州'，便于匹配 LocationID 映射表"""
    for suffix in ("市", "地区", "盟", "州"):
        if city.endswith(suffix) and len(city) > 2:
            return city[: -len(suffix)]
    return city


user_ids = ["1001", "1002", "1003", "1004", "1005", "1006", "1007", "1008", "1009", "1010",]
external_data = {}

@tool(description="从向量存储中检索参考资料")
def rag_summarize(query: str) -> str:
    return rag.rag_summarize(query)

@tool(description="获取指定城市的实时天气，以消息字符串的形式返回")
def get_weather(city: str) -> str:
    # API Key 从环境变量读取（QWEATHER_API_KEY）
    api_key = os.environ.get("QWEATHER_API_KEY")
    api_host = weather_conf.get("api_host", "")
    if not api_key or not api_host:
        return f"天气服务未配置，暂无法获取{city}天气"

    location_id = CITY_IDS.get(normalize_city_name(city))
    if not location_id:
        return f"暂不支持{city}的天气查询，可查询：{'、'.join(CITY_IDS.keys())}"

    base_url = f"https://{api_host}"
    try:
        now = requests.get(f"{base_url}/v7/weather/now",
                           params={"location": location_id, "key": api_key}, timeout=8).json()
        if now.get("code") != "200":
            return f"获取{city}天气失败：{now.get('code', 'unknown')}"

        n = now["now"]
        # 空气质量接口需要更高订阅（当前返回 403），失败时降级为不展示 AQI
        aqi_text = ""
        try:
            air = requests.get(f"{base_url}/v7/air/now",
                               params={"location": location_id, "key": api_key}, timeout=8).json()
            if air.get("code") == "200":
                aqi_text = f"，AQI{air['now']['aqi']}"
        except Exception:
            pass

        return (f"城市{city}天气为{n['text']}，气温{n['temp']}摄氏度，"
                f"空气湿度{n['humidity']}%，{n['windDir']}{n['windScale']}级"
                f"{aqi_text}，最近1小时降水{n['precip']}mm")
    except Exception as e:
        return f"获取{city}天气失败：{str(e)}"

@tool(description="获取用户所在城市的名称，以纯字符串形式返回")
def get_user_location() -> str:
    try:
        resp = requests.get("http://ip-api.com/json/?lang=zh-CN", timeout=5).json()
        return resp.get("city") or "未知"
    except Exception:
        return "未知"

@tool(description="获取用户的ID，以纯字符串形式返回")
def get_user_id() -> str:
    return random.choice(user_ids)

@tool(description="获取当前月份，以纯字符串形式返回")
def get_current_month() -> str:
    return datetime.now().strftime("%Y-%m")

def generate_external_data():
    """
        {
            "user_id": {
                "month" : {"特征": xxx, "效率": xxx, ...}
                "month" : {"特征": xxx, "效率": xxx, ...}
                "month" : {"特征": xxx, "效率": xxx, ...}
                ...
            },
            "user_id": {
                "month" : {"特征": xxx, "效率": xxx, ...}
                "month" : {"特征": xxx, "效率": xxx, ...}
                "month" : {"特征": xxx, "效率": xxx, ...}
                ...
            },
            "user_id": {
                "month" : {"特征": xxx, "效率": xxx, ...}
                "month" : {"特征": xxx, "效率": xxx, ...}
                "month" : {"特征": xxx, "效率": xxx, ...}
                ...
            },
            ...
        }
        :return:
        """
    if not external_data:
        external_data_path = get_abs_path(agent_conf["external_data_path"])

        if not os.path.exists(external_data_path):
            raise FileNotFoundError(f"外部数据文件{external_data_path}不存在")

        with open(external_data_path, 'r', encoding='utf-8') as f:
            for line in f.readlines()[1:]:
                arr: list[str] = line.strip().split(",")

                user_id: str = arr[0].replace('"', "")
                feature: str = arr[1].replace('"', "")
                efficiency: str = arr[2].replace('"', "")
                consumables: str = arr[3].replace('"', "")
                comparison: str = arr[4].replace('"', "")
                time: str = arr[5].replace('"', "")

                if user_id not in external_data:
                    external_data[user_id] = {}

                external_data[user_id][time] = {
                    "特征": feature,
                    "效率": efficiency,
                    "消耗": consumables,
                    "对比": comparison,
                }

@tool(description="从外部系统中获取指定用户在指定月份的使用记录，以纯字符串形式返回， 如果未检索到返回空字符串")
def fetch_external_data(user_id: str, month: str) -> str:
    generate_external_data()

    month_data = external_data.get(user_id, {}).get(month)
    if not month_data:
        logger.warning(f"[fetch_external_data]未检索到用户{user_id}在{month}的使用记录")
        return ""

    return month_data


@tool(description="无入参，无返回值，调用后触发中间件自动为报告生成的场景动态注入上下文信息，为后续提示词切换提供上下文信息")
def fill_context_for_report():
    return "fill_context_for_report已调用"


# if __name__ == "__main__":
#     print(fetch_external_data("1005", "2025-01"))















