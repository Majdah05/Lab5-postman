"""Test an isolated live HTTP server and export its actual responses for Postman."""
import json
import sys
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, build_opener, ProxyHandler
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app as lab
from werkzeug.serving import make_server

ROOT = Path(__file__).resolve().parents[1]
USER = {'name': 'John Doe', 'email': 'john@example.com', 'phone': '067765434567',
        'address': 'John Doe Street, Innsbruck', 'country': 'Austria'}


def main():
    original = lab.DATABASE
    records = []
    opener = build_opener(ProxyHandler({}))
    with tempfile.TemporaryDirectory() as directory:
        lab.DATABASE = Path(directory) / 'database.db'
        lab.create_db_table()
        server = make_server('localhost', 5000, lab.app)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        def send(method, path, body=None, expected=200):
            data = json.dumps(body).encode() if body is not None else None
            headers = {'Content-Type': 'application/json'} if data is not None else {}
            request = Request('http://localhost:5000' + path, data=data, headers=headers, method=method)
            try:
                response = opener.open(request, timeout=5)
            except HTTPError as error:
                response = error
            with response:
                raw = response.read().decode()
                record = {'method': method, 'path': path, 'request_body': body,
                          'code': response.status, 'status': response.reason,
                          'headers': [{'key': k, 'value': v} for k, v in response.headers.items()],
                          'body': raw}
            records.append(record)
            assert record['code'] == expected, record
            print(f"PASS {method} {path} -> {expected}")
            return json.loads(raw), record

        try:
            empty, empty_record = send('GET', '/api/users')
            assert empty == []
            user, post_record = send('POST', '/api/users/add', USER)
            assert user == dict(USER, user_id=1)
            users, list_record = send('GET', '/api/users')
            assert users == [user]
            single, get_record = send('GET', f"/api/users/{user['user_id']}")
            assert single == user
            updated = dict(user, name='Jane Doe', country='Lebanon')
            result, put_record = send('PUT', '/api/users/update', updated)
            assert result == updated
            result, _ = send('GET', f"/api/users/{user['user_id']}")
            assert result == updated
            result, delete_record = send('DELETE', f"/api/users/delete/{user['user_id']}")
            assert result == {'status': 'User deleted successfully'}
            result, _ = send('GET', '/api/users')
            assert result == []
            send('GET', '/api/users/999', expected=404)
            send('PUT', '/api/users/update', dict(USER, user_id=999), expected=404)
            send('DELETE', '/api/users/delete/999', expected=404)
            send('POST', '/api/users/add', {}, expected=400)
            send('PUT', '/api/users/update', USER, expected=400)
            send('GET', '/api/users/not-an-id', expected=400)
        finally:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()
            lab.DATABASE = original

    def item(name, record, path=None, body=None, extra=None):
        request = {'method': record['method'], 'header': [],
                   'url': '{{base_url}}' + (path or record['path'])}
        request_body = body if body is not None else record['request_body']
        if request_body is not None:
            request['header'] = [{'key': 'Content-Type', 'value': 'application/json'}]
            raw = json.dumps(request_body, indent=2).replace('"{{user_id}}"', '{{user_id}}')
            request['body'] = {'mode': 'raw', 'raw': raw, 'options': {'raw': {'language': 'json'}}}
        def example(response_record):
            actual_request = {'method': response_record['method'], 'header': request['header'],
                              'url': '{{base_url}}' + response_record['path']}
            if response_record['request_body'] is not None:
                actual_request['body'] = {'mode': 'raw', 'raw': json.dumps(response_record['request_body'], indent=2),
                                          'options': {'raw': {'language': 'json'}}}
            return {'name': 'Successful live response', 'originalRequest': actual_request,
                    'status': response_record['status'], 'code': response_record['code'],
                    '_postman_previewlanguage': 'json', 'header': response_record['headers'],
                    'cookie': [], 'body': response_record['body']}
        scripts = ['pm.test("HTTP 200", function () { pm.response.to.have.status(200); });']
        if record['method'] == 'POST':
            scripts.append('if (pm.response.code === 200) { pm.collectionVariables.set("user_id", pm.response.json().user_id); }')
        return {'name': name, 'request': request,
                'response': [example(record)] + ([example(extra)] if extra else []),
                'event': [{'listen': 'test', 'script': {'type': 'text/javascript', 'exec': scripts}}]}

    collection = {'info': {'_postman_id': str(uuid4()), 'name': 'Flask user app',
                          'description': 'Lab 5. Run in listed order. POST saves user_id for GET, PUT and DELETE. Examples were captured from live localhost HTTP responses.',
                          'schema': 'https://schema.getpostman.com/json/collection/v2.1.0/collection.json'},
                  'variable': [{'key': 'user_id', 'value': '', 'type': 'string'}],
                  'item': [item('GET all users', list_record, extra=empty_record),
                           item('POST add user', post_record),
                           item('GET a single user', get_record, '/api/users/{{user_id}}'),
                           item('PUT update user', put_record, body=dict(updated, user_id='{{user_id}}')),
                           item('DELETE user', delete_record, '/api/users/delete/{{user_id}}')]}
    environment = {'id': str(uuid4()), 'name': 'Local',
                   'values': [{'key': 'base_url', 'value': 'http://localhost:5000', 'type': 'default', 'enabled': True}],
                   '_postman_variable_scope': 'environment'}
    output = ROOT / 'postman'
    output.mkdir(exist_ok=True)
    for name, value in [('Flask_user_app.postman_collection.json', collection), ('Local.postman_environment.json', environment)]:
        (output / name).write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
    evidence = {'captured_at': datetime.now(timezone.utc).isoformat(),
                'base_url': 'http://localhost:5000', 'passed_requests': len(records), 'requests': records}
    (ROOT / 'tests' / 'http_results.json').write_text(json.dumps(evidence, indent=2) + '\n', encoding='utf-8')
    print(f'Exported five Postman requests with six real response examples; {len(records)} live HTTP checks passed.')


if __name__ == '__main__':
    main()
