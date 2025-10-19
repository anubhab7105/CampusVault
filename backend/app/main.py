import os
from flask import Flask, jsonify
from app.config import SQLALCHEMY_DATABASE_URI, SQLALCHEMY_TRACK_MODIFICATIONS, UPLOAD_FOLDER, MAX_CONTENT_LENGTH
from app.models.db_models import db
from app.routes.auth_routes import bp as auth_bp
from app.routes.user_routes import bp as user_bp
from app.routes.upload_routes import bp as upload_bp
from app.routes.notice_routes import bp as notice_bp
from app.routes.complaint_routes import bp as complaint_bp
from app.routes.chat_routes import bp as chat_bp

def create_app():
    app = Flask(__name__, static_folder=None)
    # basic configuration
    app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = SQLALCHEMY_TRACK_MODIFICATIONS
    app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
    app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

    # initialize db
    db.init_app(app)

    # register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(upload_bp)
    app.register_blueprint(notice_bp)
    app.register_blueprint(complaint_bp)
    app.register_blueprint(chat_bp)

    @app.route("/api/ping")
    def ping():
        return jsonify({"message": "pong", "status": "ok"})

    # create DB tables if not present
    with app.app_context():
        os.makedirs(os.path.join(os.path.dirname(__file__), "static_uploads"), exist_ok=True)
        db.create_all()

    return app

if __name__ == "__main__":
    app = create_app()
    port = int(os.getenv("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
