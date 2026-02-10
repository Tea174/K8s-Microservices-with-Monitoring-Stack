import React, { useState, useEffect } from 'react';
import './App.css';

const API_URL = '';

function App() {
    const [tasks, setTasks] = useState([]);
    const [newTask, setNewTask] = useState('');
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        fetchTasks();
    }, []);

    const fetchTasks = async () => {
        try {
            setLoading(true);
            const response = await fetch(`${API_URL}/api/tasks`);
            if (!response.ok) throw new Error('Failed to fetch tasks');
            const data = await response.json();
            setTasks(data);
            setError(null);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const addTask = async (e) => {
        e.preventDefault();
        if (!newTask.trim()) return;

        try {
            const response = await fetch(`${API_URL}/api/tasks`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title: newTask }),
            });
            if (!response.ok) throw new Error('Failed to add task');
            setNewTask('');
            fetchTasks();
        } catch (err) {
            setError(err.message);
        }
    };

    const deleteTask = async (id) => {
        try {
            const response = await fetch(`${API_URL}/api/tasks/${id}`, {
                method: 'DELETE',
            });
            if (!response.ok) throw new Error('Failed to delete task');
            fetchTasks();
        } catch (err) {
            setError(err.message);
        }
    };

    const toggleTask = async (id, completed) => {
        try {
            const response = await fetch(`${API_URL}/api/tasks/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ completed: !completed }),
            });
            if (!response.ok) throw new Error('Failed to update task');
            fetchTasks();
        } catch (err) {
            setError(err.message);
        }
    };

    return (
        <div className="App">
            <div className="container">
                <h1>📝 Task Manager</h1>

                <form onSubmit={addTask} className="task-form">
                    <input
                        type="text"
                        value={newTask}
                        onChange={(e) => setNewTask(e.target.value)}
                        placeholder="Add a new task..."
                        className="task-input"
                    />
                    <button type="submit" className="add-button">Add</button>
                </form>

                {error && <div className="error">Error: {error}</div>}
                {loading && <div className="loading">Loading tasks...</div>}

                <div className="tasks-list">
                    {tasks.length === 0 && !loading && (
                        <p className="empty-message">No tasks yet. Add one above!</p>
                    )}
                    {tasks.map((task) => (
                        <div key={task.id} className={`task-item ${task.completed ? 'completed' : ''}`}>
                            <input
                                type="checkbox"
                                checked={task.completed}
                                onChange={() => toggleTask(task.id, task.completed)}
                            />
                            <span className="task-title">{task.title}</span>
                            <button onClick={() => deleteTask(task.id)} className="delete-button">
                                Delete
                            </button>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}

export default App;