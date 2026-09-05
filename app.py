from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import unquote
import sqlite3, json, threading, webbrowser

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / 'pricing.db'
HTML_PATH = BASE_DIR / 'templates' / 'index.html'
HOST, PORT = '127.0.0.1', 4500

def init_db():
    with sqlite3.connect(DB_PATH) as con:
        con.execute('''CREATE TABLE IF NOT EXISTS storage (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )''')
        con.commit()

def get_value(key):
    with sqlite3.connect(DB_PATH) as con:
        row = con.execute('SELECT value FROM storage WHERE key=?', (key,)).fetchone()
    return json.loads(row[0]) if row else None

def set_value(key, value):
    raw = json.dumps(value, ensure_ascii=False)
    with sqlite3.connect(DB_PATH) as con:
        con.execute('''INSERT INTO storage(key,value,updated_at) VALUES(?,?,CURRENT_TIMESTAMP)
                       ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=CURRENT_TIMESTAMP''', (key, raw))
        con.commit()

class Handler(BaseHTTPRequestHandler):
    def send_json(self, obj, status=200):
        data = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == '/' or self.path.startswith('/?'):
            data = HTML_PATH.read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        if self.path.startswith('/api/storage/'):
            key = unquote(self.path[len('/api/storage/'):])
            value = get_value(key)
            if value is None:
                self.send_json({'error': 'not found'}, 404)
            else:
                self.send_json({'value': value})
            return
        self.send_error(404)

    def do_PUT(self):
        if not self.path.startswith('/api/storage/'):
            self.send_error(404); return
        key = unquote(self.path[len('/api/storage/'):])
        try:
            length = int(self.headers.get('Content-Length', '0'))
            body = json.loads(self.rfile.read(length).decode('utf-8') or '{}')
            if 'value' not in body:
                self.send_json({'error': 'value required'}, 400); return
            set_value(key, body['value'])
            self.send_json({'ok': True})
        except Exception as e:
            self.send_json({'error': str(e)}, 500)

    def log_message(self, format, *args):
        pass

if __name__ == '__main__':
    init_db()
    url = f'http://{HOST}:{PORT}'
    threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    print(f'Pricing app: {url}')
    print('برای بستن برنامه Ctrl+C را بزنید.')
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
