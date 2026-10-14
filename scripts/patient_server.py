"""Local-only dashboard and survival research API; no patient inputs are logged."""
import argparse
import json
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import joblib
from patient_survival import predict
from treatment_assignment import predict_assignment
from patient_studies import ARCHIVES


class Handler(SimpleHTTPRequestHandler):
    models=Path(".runtime/patient-studies/models")
    cache={}

    def do_POST(self):
        if self.path not in {"/api/predict", "/api/treatment-assignment"}: self.send_error(404); return
        try:
            length=int(self.headers.get("Content-Length","0"))
            if not 0<length<=4096: raise ValueError("Request size is invalid")
            request=json.loads(self.rfile.read(length))
            cohort=request.get("cohort")
            if cohort not in ARCHIVES: raise ValueError("Unknown cancer study")
            if self.path == "/api/treatment-assignment":
                key = f"surgery-{cohort}"
                if key not in self.cache: self.cache[key]=joblib.load(self.models/f"surgery-{cohort.lower()}.joblib")
                result=predict_assignment(self.cache[key],request.get("features",{}))
            else:
                if cohort not in self.cache: self.cache[cohort]=joblib.load(self.models/f"{cohort.lower()}.joblib")
                result=predict(self.cache[cohort],request.get("features",{}))
            body=json.dumps(result,allow_nan=False).encode()
            self.send_response(200)
        except (ValueError,KeyError,TypeError,FileNotFoundError) as error:
            body=json.dumps({"error":str(error)}).encode()
            self.send_response(400)
        self.send_header("Content-Type","application/json")
        self.send_header("Cache-Control","no-store")
        self.send_header("Content-Length",str(len(body)))
        self.end_headers(); self.wfile.write(body)

    def log_message(self,format,*args):
        # Request bodies and model input values are not written to logs.
        pass


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site",type=Path,default=Path(".runtime/patient-site"))
    parser.add_argument("--models",type=Path,default=Path(".runtime/patient-studies/models"))
    parser.add_argument("--port",type=int,default=8766)
    args=parser.parse_args(); Handler.models=args.models
    server=ThreadingHTTPServer(("127.0.0.1",args.port),partial(Handler,directory=str(args.site)))
    print(f"Cancer Patient Atlas: http://127.0.0.1:{args.port} (local only)",flush=True)
    server.serve_forever()
