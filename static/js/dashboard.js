// Dashboard functionality
document.addEventListener('DOMContentLoaded', function() {
    // Initialize clock
    updateClock();
    setInterval(updateClock, 1000);
    
    // Initialize exp bar
    updateExpBar();
    
    // Handle task completion
    document.querySelectorAll('.complete-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const taskItem = this.closest('.task-item');
            const taskId = taskItem.dataset.id;
            completeTask(taskId);
        });
    });
    
    // Handle task removal
    document.querySelectorAll('.remove-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const taskId = this.dataset.id;
            removeTask(taskId);
        });
    });
    
    // Handle daily task toggles
    document.querySelectorAll('.daily-checkbox').forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            const taskId = this.dataset.taskId;
            const isDaily = this.checked;
            toggleDailyTask(taskId, isDaily);
        });
    });
    
    // Handle predefined task selection
    const predefinedTaskSelect = document.getElementById('predefined-task');
    if (predefinedTaskSelect) {
        predefinedTaskSelect.addEventListener('change', function() {
            const selectedOption = this.options[this.selectedIndex];
            if (selectedOption.value) {
                const expValue = selectedOption.dataset.exp;
                document.getElementById('task-exp').value = expValue;
            }
        });
    }
    
    // Handle new task form submission
    const newTaskForm = document.getElementById('new-task-form');
    if (newTaskForm) {
        newTaskForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const formData = new FormData(this);
            addNewTask(formData);
        });
    }
    
    // Custom task modal functionality
    const customTaskBtn = document.getElementById('custom-task-btn');
    const customTaskModal = document.getElementById('custom-task-modal');
    const closeModalBtn = document.querySelector('.close-modal');
    
    if (customTaskBtn && customTaskModal) {
        customTaskBtn.addEventListener('click', function() {
            customTaskModal.style.display = 'block';
        });
        
        closeModalBtn.addEventListener('click', function() {
            customTaskModal.style.display = 'none';
        });
        
        // Close modal when clicking outside
        window.addEventListener('click', function(e) {
            if (e.target === customTaskModal) {
                customTaskModal.style.display = 'none';
            }
        });
    }
    
    // Handle custom task form submission
    const customTaskForm = document.getElementById('custom-task-form');
    if (customTaskForm) {
        customTaskForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const formData = new FormData(this);
            
            // Show success message instead of actually submitting
            // This is a frontend-only implementation as requested
            customTaskModal.style.display = 'none';
            alert('Thank you! Your task suggestion has been sent to moderators for review.');
            
            // Reset form
            this.reset();
        });
    }
});

// Update the clock display
function updateClock() {
    const now = new Date();
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    const seconds = String(now.getSeconds()).padStart(2, '0');
    
    const timeString = `${hours}:${minutes}:${seconds}`;
    document.getElementById('clock').textContent = timeString;
    
    // Check if it's a new day (midnight) to refresh tasks
    if (hours === '00' && minutes === '00' && seconds === '00') {
        location.reload();
    }
}

// Update the experience bar
function updateExpBar() {
    // Calculate daily exp from completed tasks
    let dailyExp = 0;
    document.querySelectorAll('.task-item.completed').forEach(task => {
        dailyExp += parseInt(task.dataset.exp);
    });
    
    // Max exp is 500
    const maxExp = 500;
    const percentage = Math.min((dailyExp / maxExp) * 100, 100);
    
    // Update the exp bar
    const expBar = document.getElementById('exp-bar');
    expBar.style.width = `${percentage}%`;
    
    // Update the exp text
    document.getElementById('current-exp').textContent = dailyExp;
}

// Mark a task as complete
function completeTask(taskId) {
    fetch(`/api/tasks/${taskId}/complete`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Update task UI
            const taskItem = document.querySelector(`.task-item[data-id="${taskId}"]`);
            taskItem.classList.add('completed');
            
            // Update complete button
            const completeBtn = taskItem.querySelector('.complete-btn');
            completeBtn.disabled = true;
            completeBtn.querySelector('i').classList.remove('fa-circle');
            completeBtn.querySelector('i').classList.add('fa-check-circle');
            
            // Update exp bar
            updateExpBar();
            
            // Update total exp
            const totalExpElement = document.getElementById('total-exp');
            totalExpElement.textContent = parseInt(totalExpElement.textContent) + data.exp_gained;
        } else {
            alert('Error: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('An error occurred. Please try again.');
    });
}

// Remove a task
function removeTask(taskId) {
    if (confirm('Are you sure you want to remove this task?')) {
        fetch(`/api/tasks/${taskId}`, {
            method: 'DELETE',
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const taskItem = document.querySelector(`.task-item[data-id="${taskId}"]`);
                taskItem.remove();
                
                // Update exp bar in case it was a completed task
                updateExpBar();
            } else {
                alert('Error: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred. Please try again.');
        });
    }
}

// Toggle daily task setting
function toggleDailyTask(taskId, isDaily) {
    fetch(`/api/tasks/${taskId}/toggle-daily`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ is_daily: isDaily })
    })
    .then(response => response.json())
    .then(data => {
        if (!data.success) {
            alert('Error: ' + data.error);
            // Revert checkbox if there was an error
            const checkbox = document.querySelector(`.daily-checkbox[data-task-id="${taskId}"]`);
            checkbox.checked = !isDaily;
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('An error occurred. Please try again.');
        // Revert checkbox
        const checkbox = document.querySelector(`.daily-checkbox[data-task-id="${taskId}"]`);
        checkbox.checked = !isDaily;
    });
}

// Add a new task
function addNewTask(formData) {
    fetch('/api/tasks', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Refresh page to show new task
            location.reload();
        } else {
            alert('Error: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('An error occurred. Please try again.');
    });
}