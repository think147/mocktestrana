"""Full end-to-end self-test of the BIPARD mock test app."""
import re, sys, requests, uuid

BASE = 'http://127.0.0.1:5000'
passed = 0
failed = 0
test_username = f"bot_{uuid.uuid4().hex[:6]}"
test_password = "test1234"

def check(label, condition, detail=''):
    global passed, failed
    status = 'PASS' if condition else 'FAIL'
    print(f'  {status}  {label}' + (f'  ({detail})' if detail else ''))
    if condition:
        passed += 1
    else:
        failed += 1

print('\n=== BIPARD Mock Test - Full Self Check ===\n')

# ── 1. Login page ─────────────────────────────────────────────────────────────
print('[1] Login Page')
s = requests.Session()
r = s.get(BASE + '/login')
check('Status 200', r.status_code == 200)
check('Has login form', 'password' in r.text.lower())

# ── 2. Signup ─────────────────────────────────────────────────────────────────
print('\n[2] Signup new user')
r = s.post(BASE + '/signup',
           data={'username': test_username, 'password': test_password, 'confirm': test_password},
           allow_redirects=True)
check('Signup -> 200', r.status_code == 200)
check('Landed on dashboard', 'dashboard' in r.url)

# ── 3. Dashboard ──────────────────────────────────────────────────────────────
print('\n[3] Dashboard')
r = s.get(BASE + '/dashboard')
check('Status 200', r.status_code == 200)
check('Username visible', test_username in r.text)
check('Question bank size shown (2547)', '2547' in r.text)

# ── 4. Test page ──────────────────────────────────────────────────────────────
print('\n[4] Test Page')
r = s.get(BASE + '/test')
check('Status 200', r.status_code == 200)
check('Form present', 'testForm' in r.text or 'method="post"' in r.text)
check('100 questions in HTML', r.text.count('class="question"') == 100,
      str(r.text.count('class="question"')) + ' questions')
check('total=100 hidden field', 'value="100"' in r.text)
check('Options/radio buttons present', 'type="radio"' in r.text)

# ── 5. Submit test (all correct) ──────────────────────────────────────────────
print('\n[5] Submit Test')
data = {}
# Parse total
m = re.search(r'name="total" value="(\d+)"', r.text)
total = int(m.group(1)) if m else 100
data['total'] = str(total)
# Parse all hidden fields
for m in re.finditer(r'name="([^"]+)"\s+value="([^"]*)"', r.text):
    name, val = m.group(1), m.group(2)
    if name.startswith(('question_', 'correct_', 'option_', 'correct_text_', 'explanation_')):
        data[name] = val
# Answer correctly
for i in range(1, total + 1):
    correct = data.get('correct_' + str(i), '0')
    data['q' + str(i)] = correct if correct not in ('', '-1', 'None') else '0'

r2 = s.post(BASE + '/submit', data=data, allow_redirects=True)
check('Submit -> 200', r2.status_code == 200)
check('Result page shown', 'result' in r2.url or 'result' in r2.text.lower() or 'score' in r2.text.lower() or 'marks' in r2.text.lower())
sm = re.search(r'(\d+)\s*/\s*200', r2.text)
check('Score displayed', sm is not None, sm.group(0) if sm else 'not found')
pm = re.search(r'\b(PASS|FAIL)\b', r2.text)
check('PASS/FAIL shown', pm is not None, pm.group(0) if pm else 'not found')

# ── 6. History saved on dashboard ────────────────────────────────────────────
print('\n[6] Test History Saved')
r = s.get(BASE + '/dashboard')
check('Dashboard loads after test', r.status_code == 200)
check('Test history shown', 'PASS' in r.text or 'FAIL' in r.text or '%' in r.text)

# ── 7. Wrong password blocked ─────────────────────────────────────────────────
print('\n[7] Wrong Password Blocked')
s2 = requests.Session()
r = s2.post(BASE + '/login',
            data={'username': test_username, 'password': 'wrongpassword'},
            allow_redirects=True)
check('Status 200', r.status_code == 200)
check('Error shown', 'invalid' in r.text.lower() or 'error' in r.text.lower())
check('NOT on dashboard', 'dashboard' not in r.url)

# ── 8. Correct login ──────────────────────────────────────────────────────────
print('\n[8] Correct Login')
r = s2.post(BASE + '/login',
            data={'username': test_username, 'password': test_password},
            allow_redirects=True)
check('Status 200', r.status_code == 200)
check('Redirected to dashboard', 'dashboard' in r.url)

# ── 9. Logout ─────────────────────────────────────────────────────────────────
print('\n[9] Logout')
r = s.get(BASE + '/logout', allow_redirects=True)
check('Status 200', r.status_code == 200)
check('Sent to login', 'login' in r.url)

# ── 10. Protected routes locked after logout ──────────────────────────────────
print('\n[10] Protected Routes After Logout')
for route in ['/dashboard', '/test']:
    r = s.get(BASE + route, allow_redirects=True)
    check(f'{route} -> redirects to login', 'login' in r.url)

# ── 11. PDF download ──────────────────────────────────────────────────────────
print('\n[11] PDF Download')
r = requests.get(BASE + '/download-pdf')
check('Status 200', r.status_code == 200)
check('Content-Type PDF', 'pdf' in r.headers.get('Content-Type', '').lower())
check('File size > 500KB', len(r.content) > 500_000, str(round(len(r.content)/1024)) + ' KB')
check('Valid PDF header (%PDF)', r.content[:4] == b'%PDF')

# ── Summary ───────────────────────────────────────────────────────────────────
total_checks = passed + failed
print(f'\n{"="*45}')
print(f'  RESULT:  {passed}/{total_checks} passed  |  {failed} failed')
print('='*45)
if failed == 0:
    print('  ALL CHECKS PASSED - App is working perfectly!')
else:
    print('  Some checks failed - see FAIL lines above.')
print()
sys.exit(0 if failed == 0 else 1)
