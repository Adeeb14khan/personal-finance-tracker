import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, g
import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect('finance.db')
        g.db.row_factory = sqlite3.Row
    return g.db

def init_db():
    with app.app_context():
        db = get_db()
        cursor = db.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                date DATE NOT NULL,
                description TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                target_amount REAL NOT NULL,
                current_amount REAL DEFAULT 0,
                deadline DATE
            )
        ''')
        
        db.commit()

@app.teardown_appcontext
def close_db(error):
    if hasattr(g, 'db'):
        g.db.close()


init_db()

@app.route('/')
def index():
    db = get_db()
    cursor = db.cursor()
    
    # Get recent transactions
    cursor.execute("SELECT * FROM transactions ORDER BY date DESC LIMIT 10")
    transactions = cursor.fetchall()
    
    # Calculate totals
    cursor.execute("SELECT SUM(amount) FROM transactions WHERE type='income'")
    total_income = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT SUM(amount) FROM transactions WHERE type='expense'")
    total_expense = cursor.fetchone()[0] or 0
    
    balance = total_income - total_expense
    
    # Get goals
    cursor.execute("SELECT * FROM goals")
    goals = cursor.fetchall()
    
    return render_template('index.html', 
                           transactions=transactions,
                           total_income=total_income,
                           total_expense=total_expense,
                           balance=balance,
                           goals=goals)

@app.route('/add', methods=['GET', 'POST'])
def add_transaction():
    if request.method == 'POST':
        transaction_type = request.form['type']
        amount = float(request.form['amount'])
        category = request.form['category']
        date = request.form['date']
        description = request.form['description']
        
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''
            INSERT INTO transactions (type, amount, category, date, description)
            VALUES (?, ?, ?, ?, ?)
        ''', (transaction_type, amount, category, date, description))
        db.commit()
        
        flash('Transaction added successfully!', 'success')
        return redirect(url_for('index'))
    
    return render_template('add.html')

@app.route('/reports')
def reports():
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('''
        SELECT category, SUM(amount) as total 
        FROM transactions 
        WHERE type='expense'
        GROUP BY category
    ''')
    expense_by_category = cursor.fetchall()
    
    # Monthly income vs expense
    cursor.execute('''
        SELECT strftime('%Y-%m', date) as month,
               SUM(CASE WHEN type='income' THEN amount ELSE 0 END) as income,
               SUM(CASE WHEN type='expense' THEN amount ELSE 0 END) as expense
        FROM transactions
        GROUP BY month
        ORDER BY month DESC
        LIMIT 6
    ''')
    monthly_data = cursor.fetchall()
    
    return render_template('reports.html',
                           expense_by_category=expense_by_category,
                           monthly_data=monthly_data)

@app.route('/goals', methods=['GET', 'POST'])
def manage_goals():
    if request.method == 'POST':
        name = request.form['name']
        target_amount = float(request.form['target_amount'])
        deadline = request.form['deadline']
        
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''
            INSERT INTO goals (name, target_amount, deadline)
            VALUES (?, ?, ?)
        ''', (name, target_amount, deadline))
        db.commit()
        
        flash('Goal created successfully!', 'success')
        return redirect(url_for('manage_goals'))
    
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM goals")
    goals = cursor.fetchall()
    
    return render_template('goals.html', goals=goals)

@app.route('/goal/<int:goal_id>/delete')
def delete_goal(goal_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM goals WHERE id = ?", (goal_id,))
    db.commit()
    
    flash('Goal deleted successfully!', 'success')
    return redirect(url_for('manage_goals'))

if __name__ == '__main__':
    app.run(debug=True)
