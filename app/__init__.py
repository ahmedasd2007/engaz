import os
from flask import Flask

def create_app():
    app=Flask(__name__)
    app.config.update(SECRET_KEY=os.getenv('SECRET_KEY', 'dev-only-change-this-secret'), MAX_CONTENT_LENGTH=100*1024*1024, SEND_FILE_MAX_AGE_DEFAULT=0)
    from .routes import bp
    app.register_blueprint(bp)
    return app
