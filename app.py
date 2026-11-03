from flask import Flask, render_template, request, redirect, url_for, session, send_file
import json
import random
import os
import uuid
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__,
            template_folder=os.path.join(BASE_DIR, 'templates'),
            static_folder=os.path.join(BASE_DIR, 'static'))
app.secret_key = 'bipard-mocktest-secret-key-2024'

QUESTIONS_FILE = os.path.join(BASE_DIR, 'questions.json')
USERS_FILE = os.path.join(BASE_DIR, 'users.json')
TMP_USERS_FILE = os.path.join('/tmp', 'users.json') if os.name != 'nt' else USERS_FILE


class VercelPathFix:
    """WSGI middleware to inspect Vercel environment and restore original path."""
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        # Temporary debug probe: if requesting /api/debug or /debug
        raw_path = environ.get('PATH_INFO', '')
        if raw_path == '/debug' or environ.get('HTTP_X_DEBUG'):
            status = '200 OK'
            headers = [('Content-Type', 'application/json')]
            start_response(status, headers)
            info = {k: str(v) for k, v in environ.items() if not k.startswith('wsgi.')}
            return [json.dumps(info, indent=2).encode('utf-8')]

        # Look for headers that carry the original path
        original_path = (
            environ.get('HTTP_X_MATCHED_PATH') or
            environ.get('HTTP_X_VERCEL_PATH') or
            environ.get('HTTP_X_FORWARDED_PATH') or
            environ.get('HTTP_X_ORIGINAL_PATH') or
            environ.get('HTTP_X_REWRITE_PATH') or
            environ.get('HTTP_X_INVOCATION_PATH')
        )
        if original_path:
            environ['PATH_INFO'] = original_path.split('?')[0]
        return self.wsgi_app(environ, start_response)


app.wsgi_app = VercelPathFix(app.wsgi_app)


def load_questions():
    with open(QUESTIONS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_users():
    if os.path.exists(TMP_USERS_FILE) and TMP_USERS_FILE != USERS_FILE:
        try:
            with open(TMP_USERS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_users(users):
    try:
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
    except (OSError, IOError, PermissionError):
        try:
            with open(TMP_USERS_FILE, 'w', encoding='utf-8') as f:
                json.dump(users, f, ensure_ascii=False, indent=2)
        except Exception:
            pass


@app.route('/')
@app.route('/api/index')
@app.route('/debug')
def index():
    if request.path == '/debug' or request.headers.get('x-debug'):
        return {k: str(v) for k, v in request.environ.items() if not k.startswith('wsgi.')}
    if 'user' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not password:
            return render_template('login.html', error='Username and password required')

        users = load_users()
        if username in users and users[username]['password'] == password:
            session['user'] = username
            # Assign a roll number if not already set
            if 'roll' not in users[username]:
                users[username]['roll'] = str(uuid.uuid4())[:14].upper()
                save_users(users)
            session['roll'] = users[username].get('roll', username[:8].upper())
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error='Invalid credentials')

    return render_template('login.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        confirm = request.form.get('confirm', '').strip()

        if not username or not password:
            return render_template('signup.html', error='Username and password required')

        if len(password) < 4:
            return render_template('signup.html', error='Password must be at least 4 characters')

        if password != confirm:
            return render_template('signup.html', error='Passwords do not match')

        users = load_users()
        if username in users:
            return render_template('signup.html', error='Username already exists')

        roll = str(uuid.uuid4())[:14].upper()
        users[username] = {'password': password, 'tests': [], 'roll': roll}
        save_users(users)
        session['user'] = username
        session['roll'] = roll
        return redirect(url_for('dashboard'))

    return render_template('signup.html')


@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))

    users = load_users()
    user = users.get(session['user'], {})
    tests = user.get('tests', [])

    return render_template('dashboard.html',
                           username=session['user'],
                           tests=tests,
                           bank_size=len(load_questions()))


@app.route('/test')
def test():
    if 'user' not in session:
        return redirect(url_for('login'))

    bank = load_questions()
    total = 100
    if len(bank) >= total:
        selected = random.sample(bank, total)
    else:
        selected = random.choices(bank, k=total)

    for i, q in enumerate(selected, start=1):
        q_copy = dict(q)
        q_copy['_num'] = i
        selected[i - 1] = q_copy

    return render_template('test.html', questions=selected, total=total)


@app.route('/submit', methods=['POST'])
def submit():
    if 'user' not in session:
        return redirect(url_for('login'))

    total = int(request.form.get('total', '0'))
    score = 0
    details = []

    for i in range(1, total + 1):
        chosen_raw = request.form.get(f'q{i}')          # None = not attempted
        correct_raw = request.form.get(f'correct_{i}', '')
        question = request.form.get(f'question_{i}', '')
        explanation = request.form.get(f'explanation_{i}', '')
        options = []

        for opt_idx in range(4):
            opt_val = request.form.get(f'option_{i}_{opt_idx}', '')
            if opt_val:
                options.append(opt_val)

        # Parse correct answer index; -1 = no answer key
        try:
            correct_idx = int(correct_raw) if correct_raw not in ('', 'None', '-1') else -1
        except ValueError:
            correct_idx = -1

        # Parse user's chosen index; None = not attempted
        try:
            chosen_idx = int(chosen_raw) if chosen_raw is not None else None
        except ValueError:
            chosen_idx = None

        not_attempted = (chosen_idx is None)

        # Award marks only when answer key exists AND user answered correctly
        if correct_idx >= 0 and not not_attempted and chosen_idx == correct_idx:
            is_correct = True
            score += 2
        else:
            is_correct = False

        correct_text = options[correct_idx] if (0 <= correct_idx < len(options)) else ''

        details.append({
            'num': i,
            'question': question,
            'options': options,
            'chosen': chosen_idx,           # int or None
            'correct': correct_idx,         # int (-1 if no key)
            'correct_text': correct_text,
            'is_correct': is_correct,
            'not_attempted': not_attempted,
            'explanation': explanation
        })

    max_score = total * 2
    percentage = (score / max_score * 100) if max_score > 0 else 0

    # Save result to user history
    users = load_users()
    if session['user'] in users:
        test_result = {
            'score': score,
            'total': max_score,
            'percentage': percentage,
            'timestamp': datetime.now().isoformat(),
            'status': 'PASS' if percentage >= 50 else 'FAIL'
        }
        users[session['user']]['tests'].append(test_result)
        save_users(users)

    correct_count = sum(1 for d in details if d['is_correct'])
    wrong_count = sum(1 for d in details if not d['is_correct'] and not d['not_attempted'])
    not_attempted_count = sum(1 for d in details if d['not_attempted'])
    exam_date = datetime.now().strftime('%Y-%m-%d')
    roll = session.get('roll', session.get('user', 'GUEST')[:8].upper())

    return render_template('result.html',
                           score=score,
                           total=max_score,
                           percentage=percentage,
                           details=details,
                           username=session.get('user', ''),
                           correct_count=correct_count,
                           wrong_count=wrong_count,
                           not_attempted_count=not_attempted_count,
                           exam_date=exam_date,
                           session_id=roll)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/download-pdf')
def download_pdf():
    pdf_path = os.path.join(BASE_DIR, 'BIPARD_All_Questions.pdf')
    return send_file(pdf_path, as_attachment=True, download_name='BIPARD_All_Questions.pdf')


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
