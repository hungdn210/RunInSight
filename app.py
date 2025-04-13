from flask import Flask, render_template, redirect, url_for, request, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate  
from markupsafe import Markup
import plotly.graph_objs as go
import os
from models import StrengthTraining
from datetime import datetime


from models import  db, User, Workout, Feedback  


app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'hello123*')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'  
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize Extensions
from models import db  
db.init_app(app)  
migrate = Migrate(app, db)  # Initialize Flask-Migrate


# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Home Page
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/parkrun')
def parkrun_page():
    return render_template('parkrun.html')

@app.route('/blogs')
def blogs_page():
    return render_template('blogs.html')

@app.route('/course')
def course_page():
    return render_template('course.html')

# Registration Page
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        role = request.form['role']

        # Check for existing email
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already exists. Please use a different email.', 'danger')
            return redirect(url_for('register', role=role))

        # Add the user to the database
        new_user = User(username=username, email=email, password=password, role=role)
        db.session.add(new_user)
        db.session.commit()
        
        flash('Account created! Please log in.', 'success')
        return redirect(url_for('login'))

    role = request.args.get('role', 'runner')  # Defaults to 'runner'
    return render_template('register.html', role=role)

# login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['role'] = user.role  # 'runner' or 'coach'
            login_user(user)  # Ensure Flask-Login registers the user
            
            # Debugging print statements
            print("User logged in:", user.id, user.role)
            print("Session Data:", session)

            if user.role == 'runner':
                return redirect(url_for('runner_dashboard'))
            elif user.role == 'coach':
                return redirect(url_for('coach_dashboard'))
            else:
                return redirect(url_for('home'))
        else:
            flash('Invalid email or password. Please try again.', 'danger')
    
    return render_template('login.html')




@app.route('/runner', methods=['GET'])
@login_required
def runner_dashboard():
    if session.get('role') != 'runner':
        return redirect(url_for('login'))

    # Fetch workouts **logged by the runner**
    workouts = Workout.query.filter_by(user_id=session['user_id']).all()

    # **Fetch assigned workouts by a coach** (only incomplete ones)
    assigned_workouts = Workout.query.filter(
        Workout.user_id == session['user_id'],  # Assigned to this runner
        Workout.coach_id.isnot(None),  # Make sure it's from a coach
        Workout.completed == False  # Only show workouts that are **not yet completed**
    ).all()
    assigned_strengths = Workout.query.filter(
        Workout.user_id == session['user_id'],
        Workout.coach_id.isnot(None),
        Workout.completed == False,
        Workout.type == 'Strength'
    ).all()
    print(f"Assigned Workouts for Runner {session['user_id']}: {assigned_workouts}")

    # Fetch completed workouts
    completed_workouts = Workout.query.filter_by(user_id=session['user_id'], completed=True).all()
     # Fetch feedback for the logged-in runner
    feedbacks = Feedback.query.filter_by(runner_id=int(session['user_id'])).all()
    print(f"DEBUG: Fetched feedbacks for runner {session['user_id']}: {feedbacks}")


    print(f"Assigned Workouts for Runner {session['user_id']}: {assigned_workouts}")  # Debugging Output

    # Prepare data for performance insights
    distances = [workout.distance if workout.distance else 0 for workout in workouts]
    times = [workout.time_taken if workout.time_taken else 0 for workout in workouts]
    
    speeds = [
        (workout.distance / (workout.time_taken / 60)) 
        if workout.distance and workout.time_taken and workout.time_taken > 0 
        else 0 
        for workout in workouts
    ]
    
    heart_rates = [workout.heart_rate if workout.heart_rate else 0 for workout in workouts]
    dates = list(range(1, len(workouts) + 1))  # Workout indices for x-axis
    min_points = 5
    num_actual = len(dates)

    if num_actual < min_points:
        padding = min_points - num_actual
        dates += list(range(num_actual + 1, min_points + 1))
        distances += [0] * padding
    # ✅ Distance Over Time as a BAR chart now
    distance_chart = go.Figure()
    distance_chart.add_trace(go.Bar(
        x=dates, y=distances, name='Distance (km)', marker=dict(color='blue')
    ))
    distance_chart.update_layout(
        title='Distance Over Time', xaxis_title='Workout #',
        yaxis_title='Distance (km)', template='plotly_dark'
    )

    # ✅ Speed Over Time as a LINE+MARKERS chart now
    speed_chart = go.Figure()
    speed_chart.add_trace(go.Scatter(
        x=dates, y=speeds, mode='lines+markers',
        name='Speed (km/h)', line=dict(color='green', width=2),
        marker=dict(size=8)
    ))
    speed_chart.update_layout(
        title='Speed Over Time', xaxis_title='Workout #',
        yaxis_title='Speed (km/h)', template='plotly_dark'
    )


    # **Heart Rate Over Time Chart**
    heart_rate_chart = go.Figure()
    heart_rate_chart.add_trace(go.Scatter(
        x=dates, y=heart_rates, mode='lines+markers',
        name='Heart Rate (bpm)', line=dict(color='red', width=2),
        marker=dict(size=8)
    ))
    heart_rate_chart.update_layout(
        title='Heart Rate Over Time', xaxis_title='Workout #', 
        yaxis_title='Heart Rate (bpm)', template='plotly_dark'
    )

    # **Subjective Data Charts**
    moods = [workout.mood for workout in workouts]
    efforts = [workout.perceived_effort for workout in workouts]
    fatigue_levels = [workout.fatigue_level for workout in workouts]

    # **Mood Distribution Chart**
    mood_chart = go.Figure()
    mood_chart.add_trace(go.Pie(
        labels=['Happy', 'Neutral', 'Tired', 'Stressed'],
        values=[moods.count('Happy'), moods.count('Neutral'), moods.count('Tired'), moods.count('Stressed')],
        hole=0.4
    ))
    mood_chart.update_layout(title='Mood Distribution')

    # **Perceived Effort Chart**
    perceived_effort_chart = go.Figure()
    perceived_effort_chart.add_trace(go.Bar(
        x=['Easy', 'Moderate', 'Hard', 'Very Hard'],
        y=[efforts.count('Easy'), efforts.count('Moderate'), efforts.count('Hard'), efforts.count('Very Hard')],
        marker_color='orange'
    ))
    perceived_effort_chart.update_layout(
        title='Perceived Effort Levels', xaxis_title='Effort', 
        yaxis_title='Count', template='plotly_dark'
    )

    # **Fatigue Levels Chart**
    fatigue_chart = go.Figure()
    fatigue_chart.add_trace(go.Pie(
        labels=['Low', 'Moderate', 'High'],
        values=[fatigue_levels.count('Low'), fatigue_levels.count('Moderate'), fatigue_levels.count('High')],
        hole=0.4
    ))
    fatigue_chart.update_layout(title='Fatigue Levels')
    print("Completed Workouts for Runner", session['user_id'], ":", completed_workouts)

    # ✅ Use completed strength workouts from Workout table instead
    # ✅ Fetch both manual and assigned strength training sessions
    # ✅ Fetch both manual and assigned strength training sessions
    manual_strengths = StrengthTraining.query.filter_by(user_id=session['user_id']).all()
    assigned_strengths = Workout.query.filter_by(user_id=session['user_id'], completed=True, type='Strength').all()

    combined_strengths = []

    # Convert manual ones to a common format
    for s in manual_strengths:
        volume = s.sets * s.reps * s.weight if s.sets and s.reps and s.weight else 0
        combined_strengths.append(("Manual", volume))

    # Convert assigned ones
    for w in assigned_strengths:
        volume = w.sets * w.reps * w.weight if w.sets and w.reps and w.weight else 0
        combined_strengths.append(("Assigned", volume))

    # Label and volume for plotting
    labels = [f"Session {i+1} ({src})" for i, (src, _) in enumerate(combined_strengths)]
    volumes = [vol for _, vol in combined_strengths]

    # Generate the combined chart
    strength_chart = go.Figure()
    strength_chart.add_trace(go.Bar(x=labels, y=volumes, name="Training Volume (kg)", marker=dict(color="orange")))
    strength_chart.update_layout(
        title='Strength Training Volume Over Time',
        xaxis_title='Training Session',
        yaxis_title='Volume (kg)',
        template='plotly_dark'
    )


    return render_template(
        'runner_dashboard.html',
        feedbacks=feedbacks,
        workouts=workouts,
        assigned_workouts=assigned_workouts,  # Assigned Workouts Now Visible ✅
        completed_workouts=completed_workouts,
        distance_chart=Markup(distance_chart.to_html(full_html=False)),
        speed_chart=Markup(speed_chart.to_html(full_html=False)),
        heart_rate_chart=Markup(heart_rate_chart.to_html(full_html=False)),
        mood_chart=Markup(mood_chart.to_html(full_html=False)),
        perceived_effort_chart=Markup(perceived_effort_chart.to_html(full_html=False)),
        fatigue_chart=Markup(fatigue_chart.to_html(full_html=False)),
        strength_chart=Markup(strength_chart.to_html(full_html=False))
    )



@app.route('/complete_assignment/<int:workout_id>', methods=['GET', 'POST'])
@login_required
def complete_assignment(workout_id):
    workout = Workout.query.get_or_404(workout_id)
    if session.get('role') != 'runner' or workout.user_id != session['user_id']:
        flash("Unauthorized", "danger")
        return redirect(url_for('runner_dashboard'))

    if request.method == 'POST':
        try:
            print("Form Data Received:", request.form.to_dict())  # Debug

            if workout.type == 'Strength':
                workout.sets = int(request.form.get('sets'))
                workout.reps = int(request.form.get('reps'))
                workout.weight = float(request.form.get('weight') or 0)
                workout.duration = int(request.form.get('duration') or 0)
            else:
                workout.perceived_effort = request.form.get('perceived_effort')
                workout.mood = request.form.get('mood')
                workout.fatigue_level = request.form.get('fatigue_level')
                workout.breathing = request.form.get('breathing')
                workout.pain_injury = request.form.get('pain_injury')
                workout.enjoyment_motivation = request.form.get('enjoyment_motivation')
                workout.pre_run_fuel = float(request.form.get('pre_run_fuel') or 0)
                workout.pace = float(request.form.get('pace') or 0)
                workout.distance = float(request.form.get('distance') or 0)
                workout.heart_rate = int(request.form.get('heart_rate') or 0)
                workout.time_taken = int(request.form.get('time_taken') or 0)
                workout.elevation_gain = float(request.form.get('elevation_gain') or 0)
                workout.temperature = float(request.form.get('temperature') or 0)
                workout.humidity = float(request.form.get('humidity') or 0)

            workout.completed = True
            db.session.commit()

            print("✅ Workout marked completed:", workout.id)
            flash('Workout marked as completed!', 'success')
        except Exception as e:
            print("❌ Error completing workout:", str(e))
            flash("Something went wrong. Please fill all required fields.", "danger")

        return redirect(url_for('runner_dashboard'))


    return render_template('complete_assignment.html', workout=workout)




@app.route('/delete_workout/<int:workout_id>', methods=['POST'])
@login_required
def delete_workout(workout_id):
    if session.get('role') != 'runner':
        return redirect(url_for('login'))

    workout = Workout.query.get(workout_id)
    if not workout:
        flash('Workout not found!', 'danger')
        return redirect(url_for('runner_dashboard'))

    if workout.user_id != session['user_id']:
        flash('You do not have permission to delete this workout.', 'danger')
        return redirect(url_for('runner_dashboard'))

    db.session.delete(workout)
    db.session.commit()
    flash('Workout deleted successfully!', 'success')
    return redirect(url_for('runner_dashboard'))


@app.route('/add_workout', methods=['POST'])
@login_required
def add_workout():
    if session.get('role') != 'runner':
        return redirect(url_for('login'))

    if request.method == 'POST':
        data = request.form

        # ✅ Validate required fields
        required_fields = [
            'perceived_effort', 'mood', 'fatigue_level', 'breathing', 
            'pain_injury', 'enjoyment_motivation', 'pre_run_fuel', 
            'pace', 'distance', 'heart_rate', 'time_taken', 
            'elevation_gain', 'temperature', 'humidity'
        ]

        # ✅ Check for any missing fields
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            flash(f'Missing required fields: {", ".join(missing_fields)}', 'danger')
            return redirect(url_for('runner_dashboard'))

        try:
            # ✅ Convert data to appropriate types (handle empty values properly)
            def get_float(value, default=0.0):
                try:
                    return float(value) if value else default
                except ValueError:
                    return default

            def get_int(value, default=0):
                try:
                    return int(value) if value else default
                except ValueError:
                    return default

            pre_run_fuel = get_float(data.get('pre_run_fuel'), default=5.0)  
            pace = get_float(data.get('pace'))
            distance = get_float(data.get('distance'))
            heart_rate = get_int(data.get('heart_rate'))
            time_taken = get_int(data.get('time_taken'))
            elevation_gain = get_float(data.get('elevation_gain'))
            temperature = get_float(data.get('temperature'))
            humidity = get_float(data.get('humidity'))

            # ✅ Create and save the workout
            new_workout = Workout(
                user_id=session.get('user_id'),
                perceived_effort=data.get('perceived_effort'),
                mood=data.get('mood'),
                fatigue_level=data.get('fatigue_level'),
                breathing=data.get('breathing'),
                pain_injury=data.get('pain_injury'),
                enjoyment_motivation=data.get('enjoyment_motivation'),
                pre_run_fuel=pre_run_fuel,
                pace=pace,
                distance=distance,
                heart_rate=heart_rate,
                time_taken=time_taken,
                elevation_gain=elevation_gain,
                temperature=temperature,
                humidity=humidity,
                completed=False  # Mark the workout as not completed yet
            )

            db.session.add(new_workout)
            db.session.commit()

            flash('Workout added successfully!', 'success')
            print(f"✅ Workout added: {new_workout}")  # Debugging output

        except Exception as e:
            flash(f"❌ Error adding workout: {str(e)}", 'danger')
            print(f"❌ Error: {str(e)}")  # Debugging output

        return redirect(url_for('runner_dashboard'))
    
    




@app.route('/edit_workout', methods=['POST'])
@login_required
def edit_workout():
    if session.get('role') != 'runner':
        return redirect(url_for('login'))

    # Get workout ID and updated data
    workout_id = request.form.get('workout_id')
    workout = Workout.query.get(workout_id)

    if workout and workout.user_id == session['user_id']:
        workout.distance = request.form.get('distance')
        workout.time_taken = request.form.get('time_taken')
        workout.mood = request.form.get('mood')
        # Update other fields as needed

        db.session.commit()
        flash('Workout updated successfully!', 'success')
    else:
        flash('Workout not found or unauthorized!', 'danger')

    return redirect(url_for('runner_dashboard'))









# Logout
@app.route('/logout')
@login_required
def logout():
    session.clear()
    logout_user()
    return redirect(url_for('home'))

# Error Handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(403)
def forbidden(e):
    return render_template('403.html'), 403











@app.route('/coach', methods=['GET'])
@login_required
def coach_dashboard():
    if session.get('role') != 'coach':
        return redirect(url_for('login'))

    runners = User.query.filter_by(role='runner').all()
    
    # Fetch completed workouts
    completed_workouts = Workout.query.filter_by(completed=True).all()
    
    feedbacks = Feedback.query.all()

    return render_template(
        'coach_dashboard.html', 
        runners=runners, 
        completed_workouts=completed_workouts,
        feedbacks=feedbacks
    )



@app.route('/runner/<int:runner_id>', methods=['GET'])
@login_required
def view_runner(runner_id):
    if session.get('role') != 'coach':
        return redirect(url_for('login'))

    # Fetch runner details
    runner = User.query.get(runner_id)
    workouts = Workout.query.filter_by(user_id=runner_id).all()

    # Generate performance insights
    distances = [workout.distance for workout in workouts]
    speeds = [(workout.distance / (workout.time_taken / 60)) if workout.time_taken and workout.time_taken > 0 else 0 for workout in workouts]
    heart_rates = [workout.heart_rate for workout in workouts]
    dates = list(range(1, len(workouts) + 1))

    # Create Performance Charts
    distance_chart = go.Figure()
    distance_chart.add_trace(go.Scatter(x=dates, y=distances, mode='lines+markers', name='Distance (km)', line=dict(color='blue', width=2)))
    distance_chart.update_layout(
        title='Distance Over Time',
        xaxis_title='Workout #',
        yaxis_title='Distance (km)',
        template='plotly_dark',
        bargap=0.5,
        height=400,
        margin=dict(l=40, r=40, t=60, b=40),
        xaxis=dict(
            tickmode='linear',   # forces even ticks
            tick0=1,             # start from workout #1
            dtick=1,             # step of 1
            range=[1, max(5, len(dates))] 
        )
    )
    speed_chart = go.Figure()
    speed_chart.add_trace(go.Bar(x=dates, y=speeds, name='Speed (km/h)', marker=dict(color='green')))
    speed_chart.update_layout(title='Speed Over Time', xaxis_title='Workout #', yaxis_title='Speed (km/h)')

    heart_rate_chart = go.Figure()
    heart_rate_chart.add_trace(go.Scatter(x=dates, y=heart_rates, mode='lines+markers', name='Heart Rate (bpm)', line=dict(color='red', width=2)))
    heart_rate_chart.update_layout(title='Heart Rate Over Time', xaxis_title='Workout #', yaxis_title='Heart Rate (bpm)')

    # Generate Subjective Data Charts
    moods = [workout.mood for workout in workouts]
    efforts = [workout.perceived_effort for workout in workouts]
    fatigue_levels = [workout.fatigue_level for workout in workouts]

    mood_chart = go.Figure()
    mood_chart.add_trace(go.Pie(labels=['Happy', 'Neutral', 'Tired', 'Stressed'],
                                values=[moods.count('Happy'), moods.count('Neutral'), moods.count('Tired'), moods.count('Stressed')],
                                hole=0.4))
    mood_chart.update_layout(title='Mood Distribution')

    perceived_effort_chart = go.Figure()
    perceived_effort_chart.add_trace(go.Bar(x=['Easy', 'Moderate', 'Hard', 'Very Hard'],
                                           y=[efforts.count('Easy'), efforts.count('Moderate'), efforts.count('Hard'), efforts.count('Very Hard')],
                                           marker_color='orange'))
    perceived_effort_chart.update_layout(title='Perceived Effort Levels', xaxis_title='Effort', yaxis_title='Count')

    fatigue_chart = go.Figure()
    fatigue_chart.add_trace(go.Pie(labels=['Low', 'Moderate', 'High'],
                                   values=[fatigue_levels.count('Low'), fatigue_levels.count('Moderate'), fatigue_levels.count('High')],
                                   hole=0.4))
    fatigue_chart.update_layout(title='Fatigue Levels')

    return render_template(
        'view_runner.html',
        runner=runner,
        workouts=workouts,
        distance_chart=Markup(distance_chart.to_html(full_html=False)),
        speed_chart=Markup(speed_chart.to_html(full_html=False)),
        heart_rate_chart=Markup(heart_rate_chart.to_html(full_html=False)),
        mood_chart=Markup(mood_chart.to_html(full_html=False)),
        perceived_effort_chart=Markup(perceived_effort_chart.to_html(full_html=False)),
        fatigue_chart=Markup(fatigue_chart.to_html(full_html=False))
    )



@app.route('/assign_workout', methods=['POST'])
@login_required
def assign_workout():
    if session.get('role') != 'coach':
        return redirect(url_for('login'))

    runner_id = request.form.get('runner_id')
    assignment_type = request.form.get('assignment_type')

    if not runner_id or not assignment_type:
        flash('Missing runner or session type.', 'danger')
        return redirect(url_for('coach_dashboard'))

    try:
        if assignment_type == 'Workout':
            # Collect fields for workout assignment
            workout_name = request.form.get('workout_name')
            workout_type = request.form.get('workout_type')
            difficulty = request.form.get('difficulty')
            steps = request.form.get('steps')

            new_workout = Workout(
                user_id=int(runner_id),
                coach_id=session['user_id'],
                name=workout_name,
                type=workout_type,
                difficulty=difficulty,
                steps=steps,
                completed=False
            )

        elif assignment_type == 'Strength':
            # Collect strength training fields
            exercise_type = request.form.get('exercise_type')
            sets = request.form.get('sets')
            reps = request.form.get('reps')
            weight = request.form.get('weight')

            new_workout = Workout(
                user_id=int(runner_id),
                coach_id=session['user_id'],
                type='Strength',
                name=exercise_type + " Session",  # You can customize this
                exercise_type=exercise_type,
                sets=int(sets),
                reps=int(reps),
                weight=float(weight) if weight else 0,
                completed=False
            )
        else:
            flash('Invalid session type.', 'danger')
            return redirect(url_for('coach_dashboard'))

        db.session.add(new_workout)
        db.session.commit()
        flash(f'{assignment_type} session assigned successfully!', 'success')

    except Exception as e:
        flash(f'Error assigning session: {e}', 'danger')

    return redirect(url_for('coach_dashboard'))

@app.route('/give_feedback/<int:workout_id>', methods=['POST'])
@login_required
def give_feedback(workout_id):
    if session.get('role') != 'coach':
        flash("Access Denied!", "danger")
        return redirect(url_for('login'))

    feedback_text = request.form.get('feedback')
    workout = Workout.query.get_or_404(workout_id)

    if not workout.completed:
        flash("You can only provide feedback on completed workouts!", "warning")
        return redirect(url_for('coach_dashboard'))

    # ✅ Fix here — get coach_id from session
    coach_id = session['user_id']

    feedback = Feedback(
        runner_id=workout.user_id,  # the runner this feedback is for
        coach_id=coach_id,
        workout_id=workout_id,
        feedback=feedback_text,
        from_runner=False  # because it's coach giving feedback
    )
    db.session.add(feedback)
    db.session.commit()
    
    flash("Feedback sent successfully!", "success")
    return redirect(url_for('coach_dashboard'))

@app.route('/runner_feedback/<int:workout_id>', methods=['POST'])
@login_required
def runner_feedback(workout_id):
    if session.get('role') != 'runner':
        flash("Access Denied!", "danger")
        return redirect(url_for('login'))

    feedback_text = request.form.get('feedback')
    coach_id = request.form.get('coach_id')

    feedback = Feedback(
        runner_id=session['user_id'],
        coach_id=coach_id,
        workout_id=workout_id,
        feedback=feedback_text,
        from_runner=True
    )

    db.session.add(feedback)
    db.session.commit()

    flash("Feedback sent to your coach!", "success")
    return redirect(url_for('runner_dashboard'))

@app.route('/add_strength_training', methods=['POST'])
@login_required
def add_strength_training():
    if session.get('role') != 'runner':
        return redirect(url_for('login'))

    data = request.form

    new_strength = StrengthTraining(
        user_id=session['user_id'],
        exercise_type=data.get('exercise_type'),
        sets=int(data.get('sets')),
        reps=int(data.get('reps')),
        weight=float(data.get('weight') or 0),
        duration=int(data.get('duration') or 0),
        notes=data.get('notes'),
        timestamp=datetime.utcnow()
    )

    db.session.add(new_strength)
    db.session.commit()

    flash('Strength training session logged!', 'success')
    return redirect(url_for('runner_dashboard'))




















if __name__ == '__main__':
    app.run(debug=True)
