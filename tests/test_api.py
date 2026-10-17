"""Isolated API tests; never modify the project's database."""
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

import app as lab

USER = {"name": "John Doe", "email": "john@example.com", "phone": "067765434567",
        "address": "John Doe Street, Innsbruck", "country": "Austria"}


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.original_database = lab.DATABASE
        lab.DATABASE = Path(self.temp.name) / "database.db"
        lab.create_db_table()
        self.client = lab.app.test_client()

    def tearDown(self):
        lab.DATABASE = self.original_database
        self.temp.cleanup()

    def test_complete_crud_sequence(self):
        self.assertEqual(self.client.get('/api/users').json, [])
        response = self.client.post('/api/users/add', json=USER)
        self.assertEqual(response.status_code, 200)
        user = response.json
        self.assertEqual(user, dict(USER, user_id=1))
        self.assertEqual(self.client.get('/api/users').json, [user])
        self.assertEqual(self.client.get('/api/users/1').json, user)
        user['name'] = 'Jane Doe'
        self.assertEqual(self.client.put('/api/users/update', json=user).json, user)
        self.assertEqual(self.client.get('/api/users/1').json, user)
        self.assertEqual(self.client.delete('/api/users/delete/1').json,
                         {'status': 'User deleted successfully'})
        self.assertEqual(self.client.get('/api/users').json, [])

    def test_nonexistent_users(self):
        for response in (self.client.get('/api/users/999'),
                         self.client.put('/api/users/update', json=dict(USER, user_id=999)),
                         self.client.delete('/api/users/delete/999')):
            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.json, {'error': 'User not found'})

    def test_missing_and_invalid_fields(self):
        for method, path in [('post', '/api/users/add'), ('put', '/api/users/update')]:
            send = getattr(self.client, method)
            base = dict(USER, user_id=1) if method == 'put' else USER
            for field in lab.FIELDS:
                for value in [None, '', '  ', 12, [], {}]:
                    with self.subTest(method=method, field=field, value=value):
                        self.assertEqual(send(path, json=dict(base, **{field: value})).status_code, 400)
                missing = dict(base)
                del missing[field]
                self.assertEqual(send(path, json=missing).status_code, 400)
        self.assertEqual(self.client.get('/api/users').json, [])

    def test_invalid_json_bodies(self):
        for method, path in [('post', '/api/users/add'), ('put', '/api/users/update')]:
            send = getattr(self.client, method)
            for body in ['null', '[]', '42', '"text"', '{broken', '']:
                response = send(path, data=body, content_type='application/json')
                self.assertEqual(response.status_code, 400)
                self.assertIn('error', response.json)
            self.assertEqual(send(path, data='text').status_code, 415)

    def test_invalid_ids(self):
        for user_id in ['abc', '-1', '0', '1.5', '9' * 100, '9223372036854775808']:
            for path in ['/api/users/', '/api/users/delete/']:
                send = self.client.get if path == '/api/users/' else self.client.delete
                self.assertEqual(send(path + user_id).status_code, 400)
        for user_id in [None, True, -1, 0, 1.2, '1', 2**63]:
            self.assertEqual(self.client.put('/api/users/update',
                             json=dict(USER, user_id=user_id)).status_code, 400)

    def test_schema_and_non_destructive_initialization(self):
        user = lab.insert_user(USER)
        lab.create_db_table()
        self.assertEqual(lab.get_user_by_id(user['user_id']), user)
        with closing(sqlite3.connect(lab.DATABASE)) as conn:
            columns = conn.execute('PRAGMA table_info(users)').fetchall()
        self.assertEqual([(c[1], c[2], c[3], c[5]) for c in columns],
                         [('user_id', 'INTEGER', 1, 1)] + [(f, 'TEXT', 1, 0) for f in lab.FIELDS])

    def test_parameterized_sql(self):
        user = dict(USER, name="Robert'); DROP TABLE users; --")
        response = self.client.post('/api/users/add', json=user)
        self.assertEqual(response.json['name'], user['name'])
        self.assertEqual(len(self.client.get('/api/users').json), 1)

    def test_cors(self):
        response = self.client.get('/api/users', headers={'Origin': 'http://example.com'})
        self.assertEqual(response.headers['Access-Control-Allow-Origin'], 'http://example.com')
        response = self.client.options('/api/users/update', headers={
            'Origin': 'http://example.com', 'Access-Control-Request-Method': 'PUT',
            'Access-Control-Request-Headers': 'Content-Type'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('PUT', response.headers['Access-Control-Allow-Methods'])


if __name__ == '__main__':
    unittest.main()
