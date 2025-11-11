from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configure MySQL
app.config['MYSQL_HOST'] = os.getenv('MYSQL_HOST', 'localhost')
app.config['MYSQL_USER'] = os.getenv('MYSQL_USER', 'root')
app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD', '')
app.config['MYSQL_DB'] = os.getenv('MYSQL_DB', 'wpproject')
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
app.secret_key = os.getenv('SECRET_KEY', 'your_secret_key')

# Initialize MySQL
mysql = MySQL(app)

# Routes
@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('opener.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        hashed_password = generate_password_hash(password)
        
        # Insert user into database
        cur = mysql.connection.cursor()
        try:
            cur.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)",
                (username, email, hashed_password)
            )
            mysql.connection.commit()
            cur.close()
            return redirect(url_for('login'))
        except Exception as e:
            cur.close()
            return render_template('signup.html', error="Username or email already exists.")
    
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE username = %s", [username])
        user = cur.fetchone()
        cur.close()
        
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['user_id']
            session['username'] = user['username']
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error="Invalid credentials")
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    
    # Get user data
    cur = mysql.connection.cursor()
    cur.execute("SELECT username, total_exp, profile_pic FROM users WHERE user_id = %s", [user_id])
    user = cur.fetchone()
    
    # Get today's tasks
    today = datetime.date.today()
    cur.execute(
        """SELECT t.*, udt.is_daily FROM tasks t 
           LEFT JOIN user_default_tasks udt ON t.task_id = udt.task_id AND udt.user_id = t.user_id
           WHERE t.user_id = %s AND t.due_date = %s 
           ORDER BY t.exp_value DESC""",
        (user_id, today)
    )
    tasks = cur.fetchall()
    
    # Get predefined tasks for dropdown
    cur.execute(
        """SELECT * FROM predefined_tasks 
           ORDER BY category, task_name"""
    )
    predefined_task_list = cur.fetchall()
    
    # Organize predefined tasks by category
    predefined_tasks = {}
    for task in predefined_task_list:
        category = task['category']
        if category not in predefined_tasks:
            predefined_tasks[category] = []
        predefined_tasks[category].append(task)
    
    cur.close()
    
    return render_template('index.html', user=user, tasks=tasks, predefined_tasks=predefined_tasks)

@app.route('/api/tasks', methods=['GET', 'POST'])
def handle_tasks():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    user_id = session['user_id']
    
    if request.method == 'POST':
        predefined_task_id = request.form.get('predefined_task_id', None)
        task_name = None
        task_description = request.form.get('task_description', '')
        exp_value = int(request.form.get('exp_value', 0))
        is_daily = 'is_daily' in request.form
        due_date = request.form.get('due_date', datetime.date.today())
        
        cur = mysql.connection.cursor()
        
        # If using a predefined task, get its details
        if predefined_task_id and predefined_task_id != '':
            predefined_task_id = int(predefined_task_id)
            cur.execute("SELECT task_name, default_exp_value FROM predefined_tasks WHERE predefined_task_id = %s", [predefined_task_id])
            predefined_task = cur.fetchone()
            if predefined_task:
                task_name = predefined_task['task_name']
                if exp_value == 0:  # If exp value not manually set, use default
                    exp_value = predefined_task['default_exp_value']
        else:
            predefined_task_id = None
            task_name = request.form['task_name']
        
        # Insert task
        cur.execute(
            """INSERT INTO tasks 
               (user_id, task_name, task_description, exp_value, due_date, predefined_task_id) 
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (user_id, task_name, task_description, exp_value, due_date, predefined_task_id)
        )
        mysql.connection.commit()
        task_id = cur.lastrowid
        
        # If it's a daily task, mark it in user_default_tasks
        if is_daily:
            cur.execute(
                "INSERT INTO user_default_tasks (user_id, task_id, is_daily) VALUES (%s, %s, TRUE)",
                (user_id, task_id)
            )
            mysql.connection.commit()
        
        cur.close()
        
        return jsonify({"success": True, "task_id": task_id})
    
    else:  # GET
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM tasks WHERE user_id = %s", [user_id])
        tasks = cur.fetchall()
        cur.close()
        
        return jsonify(tasks)

@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    user_id = session['user_id']
    
    cur = mysql.connection.cursor()
    # Verify task belongs to user
    cur.execute("SELECT * FROM tasks WHERE task_id = %s AND user_id = %s", (task_id, user_id))
    task = cur.fetchone()
    
    if not task:
        cur.close()
        return jsonify({"error": "Task not found"}), 404
    
    # Delete from user_default_tasks first (if exists) due to foreign key constraint
    cur.execute("DELETE FROM user_default_tasks WHERE task_id = %s AND user_id = %s", (task_id, user_id))
    
    # Then delete the task
    cur.execute("DELETE FROM tasks WHERE task_id = %s", [task_id])
    mysql.connection.commit()
    cur.close()
    
    return jsonify({"success": True})

@app.route('/api/tasks/<int:task_id>/complete', methods=['POST'])
def complete_task(task_id):
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    user_id = session['user_id']
    
    cur = mysql.connection.cursor()
    # Verify task belongs to user
    cur.execute("SELECT * FROM tasks WHERE task_id = %s AND user_id = %s", (task_id, user_id))
    task = cur.fetchone()
    
    if not task:
        cur.close()
        return jsonify({"error": "Task not found"}), 404
    
    if task['is_completed']:
        cur.close()
        return jsonify({"error": "Task already completed"}), 400
    
    # Mark task as completed
    cur.execute("UPDATE tasks SET is_completed = TRUE WHERE task_id = %s", [task_id])
    
    # Add exp to user
    exp_value = task['exp_value']
    cur.execute("UPDATE users SET total_exp = total_exp + %s WHERE user_id = %s", (exp_value, user_id))
    
    # Record daily progress
    today = datetime.date.today()
    cur.execute(
        "INSERT INTO daily_records (user_id, date, exp_gained) VALUES (%s, %s, %s) "
        "ON DUPLICATE KEY UPDATE exp_gained = exp_gained + %s",
        (user_id, today, exp_value, exp_value)
    )
    
    mysql.connection.commit()
    cur.close()
    
    return jsonify({"success": True, "exp_gained": exp_value})

@app.route('/api/tasks/<int:task_id>/toggle-daily', methods=['POST'])
def toggle_daily_task(task_id):
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    user_id = session['user_id']
    data = request.json
    is_daily = data.get('is_daily', False)
    
    cur = mysql.connection.cursor()
    # Verify task belongs to user
    cur.execute("SELECT * FROM tasks WHERE task_id = %s AND user_id = %s", (task_id, user_id))
    task = cur.fetchone()
    
    if not task:
        cur.close()
        return jsonify({"error": "Task not found"}), 404
    
    if is_daily:
        # Add/update daily task setting
        cur.execute(
            """INSERT INTO user_default_tasks (user_id, task_id, is_daily) 
               VALUES (%s, %s, TRUE) 
               ON DUPLICATE KEY UPDATE is_daily = TRUE""",
            (user_id, task_id)
        )
    else:
        # Remove from daily tasks
        cur.execute(
            "DELETE FROM user_default_tasks WHERE user_id = %s AND task_id = %s",
            (user_id, task_id)
        )
    
    mysql.connection.commit()
    cur.close()
    
    return jsonify({"success": True})

@app.route('/api/penalties', methods=['POST'])
def apply_penalties():
    """Daily job to apply penalties for incomplete tasks"""
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)
    
    cur = mysql.connection.cursor()
    
    # Get all incomplete tasks from yesterday
    cur.execute(
        "SELECT user_id, SUM(exp_value) as total_penalty FROM tasks "
        "WHERE due_date = %s AND is_completed = FALSE GROUP BY user_id",
        [yesterday]
    )
    penalties = cur.fetchall()
    
    # Apply penalties to each user
    for penalty in penalties:
        user_id = penalty['user_id']
        penalty_value = penalty['total_penalty']
        
        # Update user's total exp (ensuring it doesn't go below 0)
        cur.execute(
            "UPDATE users SET total_exp = GREATEST(0, total_exp - %s) WHERE user_id = %s",
            (penalty_value, user_id)
        )
        
        # Record the penalty in daily records
        cur.execute(
            "INSERT INTO daily_records (user_id, date, exp_lost) VALUES (%s, %s, %s) "
            "ON DUPLICATE KEY UPDATE exp_lost = %s",
            (user_id, today, penalty_value, penalty_value)
        )
    
    mysql.connection.commit()
    cur.close()
    
    return jsonify({"success": True})

@app.route('/api/custom-task', methods=['POST'])
def submit_custom_task():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    user_id = session['user_id']
    task_name = request.form['task_name']
    suggested_exp_value = int(request.form['suggested_exp_value'])
    
    cur = mysql.connection.cursor()
    cur.execute(
        "INSERT INTO task_requests (user_id, task_name, suggested_exp_value) VALUES (%s, %s, %s)",
        (user_id, task_name, suggested_exp_value)
    )
    mysql.connection.commit()
    cur.close()
    
    return jsonify({"success": True})

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    
    if request.method == 'POST':
        theme = request.form.get('theme', 'light')
        notification_enabled = 'notification_enabled' in request.form
        
        cur = mysql.connection.cursor()
        cur.execute(
            "INSERT INTO user_settings (user_id, theme, notification_enabled) VALUES (%s, %s, %s) "
            "ON DUPLICATE KEY UPDATE theme = %s, notification_enabled = %s",
            (user_id, theme, notification_enabled, theme, notification_enabled)
        )
        mysql.connection.commit()
        cur.close()
        
        return redirect(url_for('dashboard'))
    
    # Get current settings
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM user_settings WHERE user_id = %s", [user_id])
    settings = cur.fetchone()
    cur.close()
    
    if not settings:
        settings = {
            'theme': 'light',
            'notification_enabled': True
        }
    
    return render_template('settings.html', settings=settings)

@app.route('/api/daily-tasks/refresh', methods=['POST'])
def refresh_daily_tasks():
    """Regenerate daily tasks for users who have recurring tasks set up"""
    today = datetime.date.today()
    
    cur = mysql.connection.cursor()
    
    # Get all user default tasks
    cur.execute(
        """SELECT udt.user_id, t.task_name, t.task_description, t.exp_value, t.predefined_task_id
           FROM user_default_tasks udt
           JOIN tasks t ON udt.task_id = t.task_id
           WHERE udt.is_daily = TRUE"""
    )
    default_tasks = cur.fetchall()
    
    # Group by user
    user_tasks = {}
    for task in default_tasks:
        user_id = task['user_id']
        if user_id not in user_tasks:
            user_tasks[user_id] = []
        user_tasks[user_id].append(task)
    
    # Create new tasks for each user
    for user_id, tasks in user_tasks.items():
        for task in tasks:
            cur.execute(
                """INSERT INTO tasks 
                   (user_id, task_name, task_description, exp_value, due_date, predefined_task_id)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (
                    user_id, 
                    task['task_name'], 
                    task['task_description'], 
                    task['exp_value'], 
                    today,
                    task['predefined_task_id']
                )
            )
            new_task_id = cur.lastrowid
            
            # Mark this as a daily task in user_default_tasks
            cur.execute(
                """INSERT INTO user_default_tasks (user_id, task_id, is_daily) 
                   VALUES (%s, %s, TRUE)""",
                (user_id, new_task_id)
            )
    
    mysql.connection.commit()
    cur.close()
    
    return jsonify({"success": True})

# Route to populate predefined tasks (for initial setup)
@app.route('/setup/predefined-tasks', methods=['GET'])
def setup_predefined_tasks():
    """Populate predefined tasks table with initial data (admin only route)"""
    # For security in production, add admin authentication check here
    
    predefined_tasks = [
        # Physical tasks
        {"task_name": "Morning Exercise", "default_exp_value": 50, "category": "Physical", "is_default": True},
        {"task_name": "10,000 Steps", "default_exp_value": 60, "category": "Physical", "is_default": True},
        {"task_name": "Gym Workout", "default_exp_value": 70, "category": "Physical", "is_default": True},
        {"task_name": "Yoga Session", "default_exp_value": 40, "category": "Physical", "is_default": False},
        {"task_name": "Sports Activity", "default_exp_value": 80, "category": "Physical", "is_default": False},
        
        # Mental tasks
        {"task_name": "Meditation", "default_exp_value": 30, "category": "Mental", "is_default": True},
        {"task_name": "Reading (30 min)", "default_exp_value": 40, "category": "Mental", "is_default": True},
        {"task_name": "Learning New Skill", "default_exp_value": 70, "category": "Mental", "is_default": False},
        {"task_name": "Journaling", "default_exp_value": 20, "category": "Mental", "is_default": False},
        
        # Productivity tasks
        {"task_name": "Complete Work Project", "default_exp_value": 100, "category": "Productivity", "is_default": False},
        {"task_name": "Organize Workspace", "default_exp_value": 30, "category": "Productivity", "is_default": False},
        {"task_name": "Plan Tomorrow", "default_exp_value": 20, "category": "Productivity", "is_default": True},
        
        # Health tasks
        {"task_name": "Drink Water (2L)", "default_exp_value": 30, "category": "Health", "is_default": True},
        {"task_name": "Healthy Meal", "default_exp_value": 40, "category": "Health", "is_default": True},
        {"task_name": "Sleep 8 Hours", "default_exp_value": 50, "category": "Health", "is_default": True}
    ]
    
    cur = mysql.connection.cursor()
    
    for task in predefined_tasks:
        cur.execute(
            """INSERT IGNORE INTO predefined_tasks 
               (task_name, default_exp_value, category, is_default)
               VALUES (%s, %s, %s, %s)""",
            (task["task_name"], task["default_exp_value"], task["category"], task["is_default"])
        )
    
    mysql.connection.commit()
    count = cur.rowcount
    cur.close()
    
    return jsonify({"success": True, "tasks_added": count})

if __name__ == '__main__':
    app.run(debug=True)