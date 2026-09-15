#!/usr/bin/env python3
"""
Xray Client Management API
Allows adding/removing clients dynamically via HTTP
"""

import json
import hmac
import hashlib
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler

XRAY_CONFIG = "/usr/local/etc/xray/config.json"
API_SECRET = "metalib-xray-secret-key-2024"

def load_config():
    with open(XRAY_CONFIG, "r") as f:
        return json.load(f)

def save_config(config):
    with open(XRAY_CONFIG, "w") as f:
        json.dump(config, f, indent=2)

def reload_xray():
    subprocess.run(["systemctl", "restart", "xray"], check=True)

def check_xray_status():
    """Check if xray service is running"""
    try:
        result = subprocess.run(["systemctl", "is-active", "xray"], capture_output=True, text=True)
        return result.stdout.strip() == "active"
    except:
        return False

def get_client_count():
    """Get number of configured clients"""
    try:
        config = load_config()
        return len(config["inbounds"][0]["settings"]["clients"])
    except:
        return 0

class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Suppress default logging

    def verify_auth(self, body):
        sig = self.headers.get("Authorization", "")
        expected = hmac.new(API_SECRET.encode(), body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(sig, expected)

    def do_GET(self):
        """Handle GET requests - health check"""
        if self.path == "/health":
            self.health_check()
        else:
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"error": "Not found"}')

    def health_check(self):
        """Return health status of xray service"""
        try:
            xray_running = check_xray_status()
            client_count = get_client_count()
            
            status = "healthy" if xray_running else "unhealthy"
            
            response = {
                "status": status,
                "xray_active": xray_running,
                "clients": client_count,
                "service": "xray-vless"
            }
            
            self.send_response(200 if xray_running else 503)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "error", "error": str(e)}).encode())

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        
        if not self.verify_auth(body):
            self.send_response(401)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"error": "Unauthorized"}')
            return

        data = json.loads(body)
        
        if self.path == "/add-client":
            self.add_client(data)
        elif self.path == "/remove-client":
            self.remove_client(data)
        elif self.path == "/list-clients":
            self.list_clients()
        else:
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"error": "Not found"}')

    def add_client(self, data):
        try:
            uuid = data["uuid"]
            email = data.get("email", uuid)
            flow = data.get("flow", "xtls-rprx-vision")
            
            config = load_config()
            clients = config["inbounds"][0]["settings"]["clients"]
            
            for c in clients:
                if c["id"] == uuid:
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"success": True, "message": "Already exists"}).encode())
                    return
            
            clients.append({"id": uuid, "email": email, "flow": flow})
            save_config(config)
            reload_xray()
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": True}).encode())
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def remove_client(self, data):
        try:
            uuid = data["uuid"]
            
            config = load_config()
            clients = config["inbounds"][0]["settings"]["clients"]
            config["inbounds"][0]["settings"]["clients"] = [c for c in clients if c["id"] != uuid]
            
            save_config(config)
            reload_xray()
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": True}).encode())
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def list_clients(self):
        try:
            config = load_config()
            clients = config["inbounds"][0]["settings"]["clients"]
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"clients": clients}).encode())
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", 8444), Handler)
    print("Xray API running on port 8444")
    server.serve_forever()
