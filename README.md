# Lab5-Postman

Software Tools Lab 5: a Flask REST API that creates, reads, updates and deletes users in SQLite. The five routes and successful JSON responses follow the lab handout. CORS is enabled for all origins as requested.

## Setup and start

Open this folder in VS Code. Use Python 3.11 or newer. In a PowerShell terminal:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

The API runs at `http://localhost:5000`. Keep this terminal running during the demonstration; stop with Ctrl+C. No virtual-environment activation is required. The root URL `/` is not an API endpoint; open `/api/users`.

The delivered virtual environment uses the computer's existing Flask 3.0.3 and Flask-Cors 4.0.0 via `include-system-site-packages = true`, because package downloads timed out. The tests below ran using that environment. On another computer, create a fresh environment and install the pinned requirements normally; do not copy `.venv` between computers.

Python includes `sqlite3`; the handout's `pip install db-sqlite3` is unnecessary. `database.db` is created next to `app.py` automatically, even when launched from a different working directory. `CREATE TABLE IF NOT EXISTS` preserves existing records. The delivered database exists and is empty after verification. It is excluded from Git because it is runtime data, and is recreated on first startup after cloning.

## Database implementation

`users` has exactly these columns: `user_id INTEGER PRIMARY KEY NOT NULL`, and `name`, `email`, `phone`, `address`, `country`, each `TEXT NOT NULL`. SQLite generates the ID.

The seven functions in `app.py` are `connect_to_db`, `create_db_table`, `insert_user`, `get_users`, `get_user_by_id`, `update_user`, and `delete_user`. SQL parameters prevent input from becoming SQL. Connection context managers commit or roll back writes, and `closing` closes connections, including reads.

Corrections to the handout include the `conn().rollback()` typo, missing connection cleanup, repeated table creation, and swallowed errors. API validation returns JSON errors instead of allowing missing fields to crash a request. Successful operations retain the handout's HTTP 200 responses and delete message.

## API requests

| Method | Route | Body | Successful response |
| --- | --- | --- | --- |
| GET | `/api/users` | None | Array of users, or `[]` |
| GET | `/api/users/<user_id>` | None | User object |
| POST | `/api/users/add` | Five text fields | Created user, including generated ID |
| PUT | `/api/users/update` | Five text fields and integer `user_id` | Updated user |
| DELETE | `/api/users/delete/<user_id>` | None | `{"status":"User deleted successfully"}` |

POST and PUT require `Content-Type: application/json`. All five text fields must be nonempty strings. PUT replaces all five fields, so supply all of them. IDs must be positive integers within SQLite's signed 64-bit range. Missing users return 404; invalid IDs, malformed JSON and invalid fields return 400; a non-JSON content type returns 415. Error responses contain an `error` field.

Run all five requests from a second PowerShell terminal:

```powershell
$base = 'http://localhost:5000'
Invoke-RestMethod "$base/api/users"
$body = @{
    name = 'John Doe'
    email = 'john@example.com'
    phone = '067765434567'
    address = 'John Doe Street, Innsbruck'
    country = 'Austria'
} | ConvertTo-Json
$user = Invoke-RestMethod "$base/api/users/add" -Method Post -ContentType 'application/json' -Body $body
Invoke-RestMethod "$base/api/users/$($user.user_id)"
Invoke-RestMethod "$base/api/users"
$user.name = 'Jane Doe'
$updated = $user | ConvertTo-Json
Invoke-RestMethod "$base/api/users/update" -Method Put -ContentType 'application/json' -Body $updated
Invoke-RestMethod "$base/api/users/$($user.user_id)"
Invoke-RestMethod "$base/api/users/delete/$($user.user_id)" -Method Delete
Invoke-RestMethod "$base/api/users"
```

## Postman graded exercise

1. Start the Flask app. Open the Postman desktop app and choose your workspace.
2. Click **Import**, choose **Files**, and select both JSON files from `postman/`: `Flask_user_app.postman_collection.json` and `Local.postman_environment.json`. Confirm the import if prompted.
3. Select **Local** as the active environment. Confirm its enabled `base_url` value is `http://localhost:5000`.
4. Open the collection named exactly **Flask user app**. All five requests use `{{base_url}}`.
5. Send requests in their listed order: GET all users, POST add user, GET a single user, PUT update user, DELETE user. The POST response script saves its generated ID in the collection variable `user_id`; the next requests use `{{user_id}}`. Send POST first if running a single-user request independently. These requests also have an HTTP 200 assertion.
6. Send GET all users after POST, GET a single user after PUT, and GET all users after DELETE to demonstrate the full CRUD sequence. On a fresh database the final response is `[]`.
7. Expand each request to inspect its saved successful example. There are six saved responses: five successful operations and an extra empty-list example. The response bodies, status codes and headers were captured from real localhost HTTP calls. The saved example's original request uses the actual captured ID; the reusable request uses `{{user_id}}`.

For the handout's browser check, open `http://localhost:5000/api/users`; after POST, also open `http://localhost:5000/api/users/<actual ID>`.

No accessible Postman or browser session was available during preparation, so direct UI import and browser verification remain manual. JSON exports and live HTTP behavior were verified locally. See the official [Postman import instructions](https://learning.postman.com/docs/getting-started/importing-and-exporting/importing-data/) and [environment guide](https://learning.postman.com/docs/sending-requests/managing-environments/).

## Tests and response evidence

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Executed result: **8 tests passed**. Coverage includes the full eight-step CRUD sequence, missing users, missing/invalid fields, malformed JSON, wrong content type, invalid IDs, exact schema, preservation of existing records, SQL parameterization and CORS. Tests use temporary databases and do not erase the project database.

To repeat the live HTTP checks and regenerate the examples, first stop any server on port 5000:

```powershell
.\.venv\Scripts\python.exe tests\capture_examples.py
```

Executed result: **14 live HTTP checks passed** (the eight-step CRUD sequence plus six error checks). This script starts a temporary server at localhost:5000, uses a temporary database, captures actual responses, shuts down the server, and writes the two Postman exports and `tests/http_results.json`. Re-running changes capture timestamps and export IDs. That evidence file includes exact response bodies and status codes. Normal `app.py` startup was verified separately.

## Git history and GitHub

The repository was initialized on `main`. The database-only implementation was committed first. Branch `api` was then created from that commit (no remote existed to pull from); the REST API, tests and Postman files were implemented and committed there. It was merged into `main` with a merge commit. Both branches are retained. No existing repository or history was overwritten.

Inspect the workflow:

```powershell
git log --all --graph --oneline --decorate
git status
git branch
```

The project is published at [Majdah05/Lab5-postman](https://github.com/Majdah05/Lab5-postman). Both `main` and `api` have been pushed, and `origin` points to this repository. To push subsequent local commits:

```powershell
git push -u origin main
git push -u origin api
```

Complete Git's browser sign-in if prompted. Never put passwords or access tokens in the project. Inspect `git remote -v` before changing the remote. The database milestone was committed locally; it was not pushed before API work because no remote was available. The subsequent push preserved that database commit and branch history.

## Submission and demonstration

- Submit the GitHub repository URL if required, plus both Postman JSON exports. If submitting files, include `app.py`, `requirements.txt`, `.gitignore`, `README.md`, `postman/`, `tests/` and the local `database.db`; exclude `.venv`, caches and logs.
- Keep the local `.git` directory for demonstrating history; a plain ZIP without it does not preserve commits. A GitHub link preserves the workflow evidence.
- Demonstrate the empty list, POST, GET list and single user, PUT and GET verification, DELETE and final empty list. Show the `Local` environment, all five requests, and saved examples under every request.
- Run the test suite and show the Git graph. Be prepared to explain parameterized SQL, generated IDs, JSON requests/responses and the HTTP methods.
- Complete the handout's Postman tutorial/workspace walkthrough in your own Postman session: [quick start](https://learning.postman.com/docs/getting-started/first-steps/overview/) and [sending requests](https://learning.postman.com/docs/sending-requests/requests/).
