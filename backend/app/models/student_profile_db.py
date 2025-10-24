from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    phone = db.Column(db.String(20))
    role = db.Column(db.String(20))
    college = db.Column(db.String(100))
    department = db.Column(db.String(100))
    degree = db.Column(db.String(50))
    year = db.Column(db.String(20))
    registration = db.Column(db.String(50))
    github = db.Column(db.String(255))
    linkedin = db.Column(db.String(255))
    bio = db.Column(db.Text)
    password_hash = db.Column(db.String(255))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def serialize(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "role": self.role,
            "college": self.college,
            "department": self.department,
            "degree": self.degree,
            "year": self.year,
            "registration": self.registration,
            "github": self.github,
            "linkedin": self.linkedin,
            "bio": self.bio,
        }
