from flask import Flask
from flask_cors import CORS
from routes.auth_routes import auth_bp
from models import db

app = Flask(__name__)
CORS(app)

# Database setup
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Register routes
app.register_blueprint(auth_bp, url_prefix="/api/auth")

@app.route('/')
def home():
    return {"message": "Backend is running!"}

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
