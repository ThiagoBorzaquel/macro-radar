from http.server import BaseHTTPRequestHandler
import json

from scripts.update import collect_data


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            data = collect_data()
            if not data["quotes"] and not data["macro"] and not data["news"]:
                raise RuntimeError("Nenhuma fonte de dados respondeu")
            body = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "public, max-age=0, s-maxage=600, stale-while-revalidate=60")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception as exc:
            print("Falha ao coletar dados para a Vercel:", exc)
            body = json.dumps({"error": "Não foi possível atualizar os dados"}).encode("utf-8")
            self.send_response(502)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
