import os
import psycopg2
from flask import Flask, jsonify, request, Response
from flask_cors import CORS
import time
from prometheus_client import Counter, Histogram, generate_latest

app = Flask(__name__)
CORS(app)

# Database configuration from environment variables
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'app-deploy-k8s-db'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'password')
}

def get_db_connection():
    """Create database connection with retry logic"""
    max_retries = 5
    retry_delay = 2

    for attempt in range(max_retries):
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            return conn
        except psycopg2.OperationalError as e:
            if attempt < max_retries - 1:
                print(f"Database connection failed. Retrying in {retry_delay}s... (Attempt {attempt + 1}/{max_retries})")
                time.sleep(retry_delay)
            else:
                raise e

def init_db():
    """Initialize database schema"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS tasks (
                                                        id SERIAL PRIMARY KEY,
                                                        title VARCHAR(255) NOT NULL,
                       completed BOOLEAN DEFAULT FALSE,
                       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                       )
                   ''')
    conn.commit()
    cursor.close()
    conn.close()

# Metrics
request_count = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint'])
request_duration = Histogram('http_request_duration_seconds', 'HTTP request duration')

# Metrics endpoint
@app.route('/metrics', methods=['GET'])
def metrics():
    return Response(generate_latest(), mimetype='text/plain')

# Health check endpoints
@app.route('/health/live', methods=['GET'])
def liveness():
    """Liveness probe - checks if app is running"""
    return jsonify({'status': 'alive'}), 200

@app.route('/health/ready', methods=['GET'])
def readiness():
    """Readiness probe - checks if app can serve traffic (DB connection)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT 1')
        cursor.close()
        conn.close()
        return jsonify({'status': 'ready', 'database': 'connected'}), 200
    except Exception as e:
        return jsonify({'status': 'not ready', 'error': str(e)}), 503

# API endpoints with metrics
@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    """Get all tasks"""
    request_count.labels(method='GET', endpoint='/api/tasks').inc()
    start_time = time.time()
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, title, completed, created_at FROM tasks ORDER BY created_at DESC')
        tasks = []
        for row in cursor.fetchall():
            tasks.append({
                'id': row[0],
                'title': row[1],
                'completed': row[2],
                'created_at': row[3].isoformat() if row[3] else None
            })
        cursor.close()
        conn.close()
        request_duration.observe(time.time() - start_time)
        return jsonify(tasks), 200
    except Exception as e:
        request_duration.observe(time.time() - start_time)
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks', methods=['POST'])
def create_task():
    """Create a new task"""
    request_count.labels(method='POST', endpoint='/api/tasks').inc()
    start_time = time.time()
    try:
        data = request.get_json()
        if not data or 'title' not in data:
            request_duration.observe(time.time() - start_time)
            return jsonify({'error': 'Title is required'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO tasks (title) VALUES (%s) RETURNING id, title, completed, created_at',
            (data['title'],)
        )
        row = cursor.fetchone()
        task = {
            'id': row[0],
            'title': row[1],
            'completed': row[2],
            'created_at': row[3].isoformat() if row[3] else None
        }
        conn.commit()
        cursor.close()
        conn.close()
        request_duration.observe(time.time() - start_time)
        return jsonify(task), 201
    except Exception as e:
        request_duration.observe(time.time() - start_time)
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    """Update a task"""
    request_count.labels(method='PUT', endpoint='/api/tasks').inc()
    start_time = time.time()
    try:
        data = request.get_json()
        conn = get_db_connection()
        cursor = conn.cursor()

        if 'completed' in data:
            cursor.execute(
                'UPDATE tasks SET completed = %s WHERE id = %s RETURNING id, title, completed, created_at',
                (data['completed'], task_id)
            )

        row = cursor.fetchone()
        if not row:
            request_duration.observe(time.time() - start_time)
            return jsonify({'error': 'Task not found'}), 404

        task = {
            'id': row[0],
            'title': row[1],
            'completed': row[2],
            'created_at': row[3].isoformat() if row[3] else None
        }
        conn.commit()
        cursor.close()
        conn.close()
        request_duration.observe(time.time() - start_time)
        return jsonify(task), 200
    except Exception as e:
        request_duration.observe(time.time() - start_time)
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    """Delete a task"""
    request_count.labels(method='DELETE', endpoint='/api/tasks').inc()
    start_time = time.time()
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM tasks WHERE id = %s RETURNING id', (task_id,))
        row = cursor.fetchone()

        if not row:
            request_duration.observe(time.time() - start_time)
            return jsonify({'error': 'Task not found'}), 404

        conn.commit()
        cursor.close()
        conn.close()
        request_duration.observe(time.time() - start_time)
        return jsonify({'message': 'Task deleted'}), 200
    except Exception as e:
        request_duration.observe(time.time() - start_time)
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Initialize database on startup
    print("Initializing database...")
    init_db()
    print("Database initialized successfully")

    # Start Flask app
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)