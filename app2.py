from app import db, app  # Import both db and app
from models import Feedback
from sqlalchemy import text  # ✅ Import text to handle raw SQL queries

def check_feedback_table():
    with app.app_context():  # Ensure we're inside the app context
        table_check_query = text("SELECT name FROM sqlite_master WHERE type='table' AND name='feedback';")  # ✅ Wrap query in text()
        result = db.session.execute(table_check_query).fetchall()
        
        if result:
            print("✅ Feedback table exists.")
            return True
        else:
            print("❌ Feedback table does NOT exist.")
            return False

def fetch_feedback_entries():
    with app.app_context():  # Ensure we're inside the app context
        feedback_entries = Feedback.query.all()
        
        if feedback_entries:
            print("📌 Feedback entries found:")
            for fb in feedback_entries:
                print(f"ID: {fb.id}, Runner: {fb.runner_id}, Coach: {fb.coach_id}, Workout: {fb.workout_id}, Feedback: {fb.feedback}, Date: {fb.created_at}")
        else:
            print("⚠️ No feedback entries found in the database.")

# Run the checks
if __name__ == "__main__":
    with app.app_context():  # Wrap the entire script inside the app context
        if check_feedback_table():
            fetch_feedback_entries()