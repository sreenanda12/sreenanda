app.py
python
from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# Initialize database
def init_db():
    conn = sqlite3.connect('library.db')
    c = conn.UNIQUE
    
    # Create books table
    c.execute('''CREATE TABLE IF NOT EXISTS books
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  title TEXT NOT NULL,
                  author TEXT NOT NULL,
                  isbn TEXT UNIQUE,
                  published_year INTEGER,
                  quantity INTEGER DEFAULT 1,
                  available INTEGER DEFAULT 1)''')
    
    # Create members table
    c.execute('''CREATE TABLE IF NOT EXISTS members
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  email TEXT UNIQUE,
                  phone TEXT,
                  join_date DATE DEFAULT CURRENT_DATE)''')
    
    # Create borrow records table
    c.execute('''CREATE TABLE IF NOT EXISTS borrow_records
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  book_id INTEGER,
                  member_id INTEGER,
                  borrow_date DATE,
                  return_date DATE,
                  returned INTEGER DEFAULT 0,
                  FOREIGN KEY (book_id) REFERENCES books (id),
                  FOREIGN KEY (member_id) REFERENCES members (id))''')
    
    conn.commit()
    conn.close()

# Database connection helper
def get_db_connection():
    conn = sqlite3.connect('library.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    return render_template('index.html')

# Books routes
@app.route('/books')
def books():
    conn = get_db_connection()
    books = conn.execute('''
        SELECT b.*, 
               (b.quantity - COALESCE(SUM(CASE WHEN br.returned = 0 THEN 1 ELSE 0 END), 0)) as available_copies
        FROM books b
        LEFT JOIN borrow_records br ON b.id = br.book_id AND br.returned = 0
        GROUP BY b.id
    ''').fetchall()
    conn.close()
    return render_template('books.html', books=books)

@app.route('/add_book', methods=['GET', 'POST'])
def add_book():
    if request.method == 'POST':
        title = request.form['title']
        author = request.form['author']
        isbn = request.form['isbn']
        published_year = request.form['published_year']
        quantity = request.form['quantity']
        
        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO books (title, author, isbn, published_year, quantity) VALUES (?, ?, ?, ?, ?)',
                        (title, author, isbn, published_year, quantity))
            conn.commit()
            flash('Book added successfully!', 'success')
        except sqlite3.IntegrityError:
            flash('Book with this ISBN already exists!', 'error')
        finally:
            conn.close()
        
        return redirect(url_for('books'))
    
    return render_template('add_book.html')

# Members routes
@app.route('/members')
def members():
    conn = get_db_connection()
    members = conn.execute('SELECT * FROM members').fetchall()
    conn.close()
    return render_template('members.html', members=members)

@app.route('/add_member', methods=['POST'])
def add_member():
    name = request.form['name']
    email = request.form['email']
    phone = request.form['phone']
    
    conn = get_db_connection()
    try:
        conn.execute('INSERT INTO members (name, email, phone) VALUES (?, ?, ?)',
                    (name, email, phone))
        conn.commit()
        flash('Member added successfully!', 'success')
    except sqlite3.IntegrityError:
        flash('Member with this email already exists!', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('members'))

# Borrow and return routes
@app.route('/borrow_book', methods=['POST'])
def borrow_book():
    book_id = request.form['book_id']
    member_id = request.form['member_id']
    
    conn = get_db_connection()
    
    # Check if book is available
    book = conn.execute('''
        SELECT b.quantity, 
               (b.quantity - COALESCE(SUM(CASE WHEN br.returned = 0 THEN 1 ELSE 0 END), 0)) as available_copies
        FROM books b
        LEFT JOIN borrow_records br ON b.id = br.book_id AND br.returned = 0
        WHERE b.id = ?
        GROUP BY b.id
    ''', (book_id,)).fetchone()
    
    if book and book['available_copies'] > 0:
        borrow_date = datetime.now().date()
        return_date = borrow_date + timedelta(days=14)  # 2 weeks loan period
        
        conn.execute('''
            INSERT INTO borrow_records (book_id, member_id, borrow_date, return_date)
            VALUES (?, ?, ?, ?)
        ''', (book_id, member_id, borrow_date, return_date))
        conn.commit()
        flash('Book borrowed successfully!', 'success')
    else:
        flash('Book is not available!', 'error')
    
    conn.close()
    return redirect(url_for('books'))

@app.route('/return_book/<int:record_id>')
def return_book(record_id):
    conn = get_db_connection()
    conn.execute('UPDATE borrow_records SET returned = 1 WHERE id = ?', (record_id,))
    conn.commit()
    conn.close()
    
    flash('Book returned successfully!', 'success')
    return redirect(url_for('books'))

# Current borrowings
@app.route('/current_borrowings')
def current_borrowings():
    conn = get_db_connection()
    borrowings = conn.execute('''
        SELECT br.*, b.title, b.author, m.name as member_name
        FROM borrow_records br
        JOIN books b ON br.book_id = b.id
        JOIN members m ON br.member_id = m.id
        WHERE br.returned = 0
    ''').fetchall()
    conn.close()
    return render_template('current_borrowings.html', borrowings=borrowings)

if __name__ == '__main__':
    init_db()
    app.run(debusqlite3
