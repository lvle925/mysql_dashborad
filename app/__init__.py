from flask import Flask
from .config import Config
from .web.routes import web_bp
import structlog
import logging

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    app.register_blueprint(web_bp)
    
    # 配置结构化日志
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer()
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
    )
    
    # 禁用部分啰嗦的日志
    logging.getLogger("asyncssh").setLevel(logging.WARNING)
    
    return app