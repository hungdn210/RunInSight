from app import app, db
from models import Workout

with app.app_context():
    db.session.query(Workout).delete()
    db.session.commit()