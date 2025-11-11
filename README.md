wpproject/
│
├── app.py                   # Main Flask application
├── .env                     # Environment variables (create this file)
│
├── static/
│   ├── css/
│   │   └── style.css        # CSS styles
│   │
│   ├── js/
│   │   └── dashboard.js     # JavaScript for dashboard functionality
│   │
│   └── images/
│       └── default.png      # Default profile picture
│
└── templates/
    ├── opener.html          # Welcome page
    ├── signup.html          # Sign up page
    ├── login.html           # Login page
    ├── index.html           # Dashboard
    └── settings.html        # Settings page

CREATE THIS DATABASE:
create database if not exists DB_NAME;
use DB_NAME;
-- Users table
CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    total_exp INT DEFAULT 0,
    profile_pic VARCHAR(255) DEFAULT 'default.png',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- Tasks table
CREATE TABLE tasks (
    task_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    task_name VARCHAR(100) NOT NULL,
    task_description TEXT,
    exp_value INT NOT NULL,
    due_date DATE NOT NULL,
    is_completed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);
-- Daily records table (for tracking daily progress)
CREATE TABLE daily_records (
    record_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    date DATE NOT NULL,
    exp_gained INT DEFAULT 0,
    exp_lost INT DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    UNIQUE KEY (user_id, date)
);
-- Settings table
CREATE TABLE user_settings (
    setting_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    theme VARCHAR(50) DEFAULT 'light',
    notification_enabled BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Predefined tasks table
CREATE TABLE predefined_tasks (
    predefined_task_id INT AUTO_INCREMENT PRIMARY KEY,
    task_name VARCHAR(100) NOT NULL,
    default_exp_value INT NOT NULL,
    category VARCHAR(50),
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- Task requests table (for user-submitted tasks)
CREATE TABLE task_requests (
    request_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    task_name VARCHAR(100) NOT NULL,
    suggested_exp_value INT NOT NULL,
    status ENUM('pending', 'approved', 'rejected') DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);
-- User default tasks table (to track daily recurring tasks per user)
CREATE TABLE user_default_tasks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    task_id INT NOT NULL,
    is_daily BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (task_id) REFERENCES tasks(task_id) ON DELETE CASCADE,
    UNIQUE KEY (user_id, task_id)
);

Changes:
-- Add a column to tasks table to reference predefined tasks
ALTER TABLE tasks ADD COLUMN predefined_task_id INT NULL;
ALTER TABLE tasks ADD FOREIGN KEY (predefined_task_id) REFERENCES predefined_tasks(predefined_task_id);


ADD Some sample data to the database and you're good to go
