from flask import Flask, request, jsonify


# -----------------------------------------------------------------------------
# 1. 核心业务逻辑 (之前我们创建的CarbonEstimator类)
# -----------------------------------------------------------------------------
class CarbonEstimator:
    """
    企业碳排放初步估算器
    - 计算范围一 (化石燃料燃烧) 和范围二 (外购电力) 的碳排放。
    - 所有排放因子数据参考自中国官方发布。
    """

    def __init__(self):
        """
        初始化估算器，加载所有后台排放因子数据。
        """
        # 范围一：化石燃料燃烧排放因子 (单位: 吨CO₂ / 活动单位)
        self.EF_SCOPE1 = {
            "gas": 21.62,  # tCO2 / 万立方米
            "diesel": 3.096,  # tCO2 / 吨
            "gasoline": 2.925,  # tCO2 / 吨
            "coal": 1.900  # tCO2 / 吨
        }

        # 范围二：区域电网电力排放因子 (单位: tCO₂ / MWh)
        # 数据来源: 生态环境部《2022年度中国区域电网平均二氧化碳排放因子》
        self.EF_GRID = {
            "North": 0.5921,  # 华北区域 (京、津、冀、晋、鲁)
            "Northeast": 0.5594,  # 东北区域 (辽、吉、黑)
            "East": 0.5703,  # 华东区域 (沪、苏、浙、皖、闽)
            "Central": 0.4233,  # 华中区域 (豫、鄂、湘、赣、川、渝)
            "Northwest": 0.4908,  # 西北区域 (陕、甘、青、宁、新)
            "South": 0.3854,  # 南方区域 (粤、桂、琼、云、贵)
            "National_Avg": 0.5386  # 全国平均
        }

    def calculate_scope1_emissions(self, fuel_data: dict) -> float:
        e_scope1 = 0.0
        for fuel_type, consumption in fuel_data.items():
            if fuel_type in self.EF_SCOPE1 and consumption is not None:
                # 确保消耗量是数值类型
                try:
                    e_scope1 += float(consumption) * self.EF_SCOPE1[fuel_type]
                except (ValueError, TypeError):
                    # 如果转换失败，可以跳过或者记录日志
                    pass
        return e_scope1

    def calculate_scope2_emissions(self, electricity_data: dict) -> float:
        consumption_kwh = electricity_data.get("consumption_kwh")
        region = electricity_data.get("region")
        if not consumption_kwh or not region or region not in self.EF_GRID:
            return 0.0

        try:
            # **已修复**: kWh 转换为 MWh 应该是除以 1000
            consumption_mwh = float(consumption_kwh) / 1000.0
        except (ValueError, TypeError):
            return 0.0

        ef_grid = self.EF_GRID[region]
        return consumption_mwh * ef_grid

    def estimate_total_emissions(self, fuel_data: dict, electricity_data: dict) -> dict:
        e_scope1 = self.calculate_scope1_emissions(fuel_data)
        e_scope2 = self.calculate_scope2_emissions(electricity_data)
        e_total = e_scope1 + e_scope2
        return {
            "total_emissions": round(e_total, 4),
            "scope1_emissions": round(e_scope1, 4),
            "scope2_emissions": round(e_scope2, 4)
        }


# -----------------------------------------------------------------------------
# 2. 创建Flask应用和API接口
# -----------------------------------------------------------------------------
app = Flask(__name__)
estimator = CarbonEstimator()  # 实例化我们的大脑


# **新增**: 增加根路径'/'的路由，用于响应平台的健康检查
@app.route('/', methods=['GET'])
def health_check():
    """
    提供一个健康的端点，用于部署平台的健康检查。
    """
    return jsonify({
        "success": True,
        "message": "Carbon emission estimation service is running."
    })


@app.route('/api/estimate', methods=['POST'])
def handle_estimation():
    """
    处理来自小程序端的碳排放估算请求。
    这是一个POST接口，接收JSON格式的数据。
    """
    try:
        # 从请求中获取JSON数据
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "请求体不能为空"}), 400

        fuel_data = data.get("fuel_data", {})
        electricity_data = data.get("electricity_data", {})

        # 调用核心逻辑进行计算
        results = estimator.estimate_total_emissions(fuel_data, electricity_data)

        # 返回成功的结果
        return jsonify({"success": True, "data": results})

    except Exception as e:
        # 如果发生任何错误，返回一个标准的错误信息
        # 在实际生产中，这里应该记录更详细的日志
        return jsonify({"success": False, "error": f"服务器内部错误: {str(e)}"}), 500
