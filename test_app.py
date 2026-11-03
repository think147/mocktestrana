import unittest
import json
import os
from app import app, load_questions, load_users, save_users

class FlaskAppTests(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_load_questions(self):
        questions = load_questions()
        self.assertIsInstance(questions, list)
        self.assertTrue(len(questions) > 0)

    def test_users_functions(self):
        users = load_users()
        self.assertIsInstance(users, dict)
        
        original_users = dict(users)
        users['dummy_test_user'] = {'password': '123', 'tests': []}
        save_users(users)
        
        new_users = load_users()
        self.assertIn('dummy_test_user', new_users)
        
        save_users(original_users)

    def test_index_redirects_to_login(self):
        response = self.app.get('/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.location)

    def test_signup_and_login(self):
        resp = self.app.get('/signup')
        self.assertEqual(resp.status_code, 200)

        resp = self.app.post('/signup', data=dict(username='newuser', password='12', confirm='12'))
        self.assertIn(b'Password must be at least 4 characters', resp.data)

        users = load_users()
        if 'newuser123' in users:
            del users['newuser123']
            save_users(users)

        resp = self.app.post('/signup', data=dict(username='newuser123', password='password123', confirm='password123'))
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/dashboard', resp.location)

        resp = self.app.get('/login')
        self.assertEqual(resp.status_code, 200)

        resp = self.app.post('/login', data=dict(username='newuser123', password='wrongpassword'))
        self.assertIn(b'Invalid credentials', resp.data)

        resp = self.app.post('/login', data=dict(username='newuser123', password='password123'))
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/dashboard', resp.location)

        users = load_users()
        if 'newuser123' in users:
            del users['newuser123']
            save_users(users)

    def test_dashboard_requires_login(self):
        response = self.app.get('/dashboard')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.location)

    def test_dashboard_with_login(self):
        users = load_users()
        if 'testuser' not in users:
            users['testuser'] = {'password': '123', 'tests': []}
            save_users(users)

        with self.app.session_transaction() as sess:
            sess['user'] = 'testuser'

        response = self.app.get('/dashboard')
        self.assertEqual(response.status_code, 200)

    def test_test_route_requires_login(self):
        response = self.app.get('/test')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.location)

    def test_test_route_with_login(self):
        users = load_users()
        if 'testuser' not in users:
            users['testuser'] = {'password': '123', 'tests': []}
            save_users(users)
            
        with self.app.session_transaction() as sess:
            sess['user'] = 'testuser'
        
        response = self.app.get('/test')
        self.assertEqual(response.status_code, 200)

    def test_submit_route_requires_login(self):
        response = self.app.post('/submit', data={'total': '10'})
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.location)

    def test_submit_route_with_login(self):
        users = load_users()
        if 'testuser' not in users:
            users['testuser'] = {'password': '123', 'tests': []}
            save_users(users)
            
        with self.app.session_transaction() as sess:
            sess['user'] = 'testuser'

        data = {
            'total': '1',
            'q1': '0',
            'correct_1': '0',
            'correct_text_1': 'Option A',
            'question_1': 'What is this?',
            'option_1_0': 'Option A',
            'option_1_1': 'Option B',
            'option_1_2': 'Option C',
            'option_1_3': 'Option D',
        }
        response = self.app.post('/submit', data=data)
        self.assertEqual(response.status_code, 200)

    def test_logout(self):
        with self.app.session_transaction() as sess:
            sess['user'] = 'testuser'
            
        response = self.app.get('/logout')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.location)
        
        # Test if session was actually cleared by making another request
        resp2 = self.app.get('/dashboard')
        self.assertEqual(resp2.status_code, 302)

if __name__ == '__main__':
    unittest.main()
