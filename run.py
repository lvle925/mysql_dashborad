import uvicorn
from asgiref.wsgi import WsgiToAsgi
from app import create_app

# 创建应用实例
app = create_app()
asgi_app = WsgiToAsgi(app)

if __name__ == '__main__':
    # 获取配置中的主机和端口
    host = app.config.get('FLASK_HOST', '0.0.0.0')
    port = app.config.get('FLASK_PORT', 5000)
    
    print(f"🚀 监控系统已启动，访问地址: http://{host}:{port}")
    
    # 启动 Uvicorn 服务器
    uvicorn.run(
        asgi_app, 
        host=host, 
        port=port, 
        log_level="info"
    )