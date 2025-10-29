from flask import Flask, render_template, request, redirect, url_for
import db
import sqlite3
from selenium_worker import get_captcha, submit_form

app = Flask(__name__)
db.init_db()

@app.route('/')
def index():
    captcha = get_captcha()
    return render_template('index.html', captcha=captcha)

@app.route('/submit', methods=['POST'])
def submit():
    case_type = request.form['case_type']
    case_number = request.form['case_number']
    case_year = request.form['case_year']
    captcha_entered = request.form['captcha_entered']
    
    conn = sqlite3.connect('case_data.db')
    cur = conn.cursor()
    cur.execute('INSERT INTO requests (case_type, case_number, case_year, captcha_entered) VALUES (?, ?, ?, ?)',
                (case_type, case_number, case_year, captcha_entered))
    request_id = cur.lastrowid
    conn.commit()
    
    result_html = submit_form(case_type, case_number, case_year, captcha_entered)
    
    cur.execute('INSERT INTO results (request_id, result_html) VALUES (?, ?)',
                (request_id, result_html))
    conn.commit()
    conn.close()
    
    return render_template('result.html', result_html=result_html)

if __name__ == '__main__':
    app.run(debug=True)
