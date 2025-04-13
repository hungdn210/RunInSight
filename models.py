from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

# Initialize SQLAlchemy
db = SQLAlchemy()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(10), nullable=False)  # 'runner' or 'coach'

    # Relationship to Workout model
    workouts = db.relationship('Workout', backref='runner', lazy=True, foreign_keys='Workout.user_id')

    # Relationship for workouts assigned by this coach
    assigned_workouts = db.relationship('Workout', backref='assigned_by', lazy=True, foreign_keys='Workout.coach_id')

    # Feedback relationships (explicit naming to avoid conflicts)
    feedback_received = db.relationship('Feedback', foreign_keys='Feedback.runner_id', back_populates='runner')
    feedback_given = db.relationship('Feedback', foreign_keys='Feedback.coach_id', back_populates='coach')

class Workout(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Foreign Keys
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Runner
    coach_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Coach who assigned the workout

    # Workout Assignment Fields
    name = db.Column(db.String(100), nullable=True)  # Name of workout
    type = db.Column(db.String(50), nullable=True)  # Type of workout: "Workout" or "Strength"
    difficulty = db.Column(db.String(50), nullable=True)  # Difficulty level
    steps = db.Column(db.Text, nullable=True)  # Workout instructions (for running)
    completed = db.Column(db.Boolean, nullable=False, default=False)  # If completed

    # Subjective Data
    perceived_effort = db.Column(db.String(50), nullable=True)
    mood = db.Column(db.String(100), nullable=True)
    fatigue_level = db.Column(db.String(50), nullable=True)
    breathing = db.Column(db.String(50), nullable=True)
    pain_injury = db.Column(db.String(50), nullable=True)
    enjoyment_motivation = db.Column(db.String(100), nullable=True)
    pre_run_fuel = db.Column(db.Float, nullable=False, default=5.0)

    # Objective Data
    pace = db.Column(db.Float, nullable=True)  # Pace in km/h
    distance = db.Column(db.Float, nullable=True)  # Distance in km
    heart_rate = db.Column(db.Integer, nullable=True)  # Avg heart rate
    time_taken = db.Column(db.Integer, nullable=True)  # Time in minutes
    elevation_gain = db.Column(db.Float, nullable=True)  # Elevation in meters
    temperature = db.Column(db.Float, nullable=True)  # Temp in degrees
    humidity = db.Column(db.Float, nullable=True)  # Humidity in %

    # Strength-specific Fields
    exercise_type = db.Column(db.String(100), nullable=True)
    sets = db.Column(db.Integer, nullable=True)
    reps = db.Column(db.Integer, nullable=True)
    weight = db.Column(db.Float, nullable=True)

    # Feedback Relationship
    feedbacks = db.relationship('Feedback', back_populates='workout', cascade="all, delete-orphan")


class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    runner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    coach_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    workout_id = db.Column(db.Integer, db.ForeignKey('workout.id'), nullable=False)
    feedback = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    from_runner = db.Column(db.Boolean, nullable=False, default=False) 

    runner = db.relationship('User', foreign_keys=[runner_id], back_populates='feedback_received')
    coach = db.relationship('User', foreign_keys=[coach_id], back_populates='feedback_given')
    workout = db.relationship('Workout', foreign_keys=[workout_id], back_populates='feedbacks')


class StrengthTraining(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    exercise_type = db.Column(db.String(100))
    sets = db.Column(db.Integer)
    reps = db.Column(db.Integer)
    weight = db.Column(db.Float)
    duration = db.Column(db.Integer)
    notes = db.Column(db.String(255))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)