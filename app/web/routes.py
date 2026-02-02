from flask import Blueprint, render_template, jsonify
from app.core.collector import DataCollector

web_bp = Blueprint('web', __name__)

@web_bp.route('/')
def index():
    return render_template('index.html')

@web_bp.route('/api/data')
async def get_dashboard_data():
    return jsonify(await DataCollector.collect_dashboard_data())

@web_bp.route('/api/check_db')
async def check_db():
    return jsonify(await DataCollector.check_db_sync())

@web_bp.route('/api/db_details/<path:ip>')
async def db_details(ip):
    return jsonify(await DataCollector.get_db_details(ip))