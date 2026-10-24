"""Loopback product server. Standard library only; no local model imports."""
import argparse
import base64
import hashlib
import io
import json
import re
import subprocess
import threading
import uuid
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from .request_contract import check_request, parse

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
API = 'repos/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench'
PREFIX = 'v0_2/tests/tools/engineering_design_mvp_v1'
ARTIFACT = 'artifacts/engineering-design-mvp-v1'
MODELS = ('tank90', 'six_normal', 'six_step')


def raw_json(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False).encode()


def gh(endpoint, payload=None, binary=False):
    args = ['gh', 'api', API + '/' + endpoint]
    if payload is not None:
        args += ['--method', 'POST', '--input', '-']
    r = subprocess.run(args, input=raw_json(payload) if payload is not None else None,
                       capture_output=True, timeout=60, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if r.returncode:
        raise ValueError('GITHUB_REQUEST_FAILED: 检查本机gh登录和权限；未向浏览器暴露凭据')
    if len(r.stdout) > 64 * 1024 * 1024:
        raise ValueError('ARTIFACT_TOO_LARGE')
    return r.stdout if binary else json.loads(r.stdout)


class Handler(BaseHTTPRequestHandler):
    def reply(self, code, value, kind='application/json; charset=utf-8'):
        raw = value if isinstance(value, bytes) else raw_json(value)
        self.send_response(code)
        for k, v in {'Content-Type': kind, 'Content-Length': str(len(raw)), 'Cache-Control': 'no-store',
                     'X-Content-Type-Options': 'nosniff',
                     'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'"}.items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(raw)

    def local(self, write=False):
        roots = ('http://127.0.0.1:' + str(self.server.server_port), 'http://localhost:' + str(self.server.server_port))
        if self.headers.get('Host') not in tuple(x.removeprefix('http://') for x in roots):
            raise ValueError('LOOPBACK_HOST_REQUIRED')
        if write and self.headers.get('Origin') not in roots:
            raise ValueError('SAME_ORIGIN_REQUIRED')

    def do_GET(self):
        try:
            self.local()
            route = urlsplit(self.path)
            if route.query:
                raise ValueError('UNKNOWN_QUERY')
            static = {'/': ('index.html', 'text/html'), '/app.mjs': ('app.mjs', 'text/javascript'),
                      '/visual-core.mjs': ('visual-core.mjs', 'text/javascript'),
                      '/visual-ui.mjs': ('visual-ui.mjs', 'text/javascript'),
                      '/core.mjs': ('core.mjs', 'text/javascript'), '/style.css': ('style.css', 'text/css'),
                      '/data/baseline.json': ('data/baseline.json', 'application/json'),
                      '/data/single_history.json': ('data/single_history.json', 'application/json'),
                      '/data/switching.json': ('data/switching.json', 'application/json'),
                      '/data/historical.json': ('data/historical.json', 'application/json')}
            if route.path in static:
                p, kind = static[route.path]
                return self.reply(200, (HERE / p).read_bytes(), kind + '; charset=utf-8')
            if route.path == '/favicon.ico':
                return self.reply(204, b'')
            if route.path == '/api/catalog':
                return self.reply(200, {'models': MODELS, 'remote_enabled': self.server.remote.get('enabled', False),
                    'hashes': {p: hashlib.sha256((HERE / p).read_bytes()).hexdigest() for p in ('data/baseline.json', 'data/historical.json', 'data/single_history.json', 'data/switching.json', 'visual-core.mjs', 'visual-ui.mjs', 'style.css')},
                    'engineering_status': 'MEMPHIS_ENGINEERING_NOT_APPROVED'})
            if route.path.startswith('/api/jobs/'):
                job_id = route.path.split('/')[-1]
                if not re.fullmatch('[a-f0-9]{12}', job_id) or job_id not in self.server.jobs:
                    raise ValueError('UNKNOWN_JOB')
                job = self.server.jobs[job_id]
                runs = gh('actions/runs?branch=' + job['branch'] + '&per_page=10')['workflow_runs']
                runs = [r for r in runs if r['head_sha'] == job['commit'] and r['path'] == '.github/workflows/engineering-design-mvp-v1.yml']
                if not runs:
                    return self.reply(200, {**job, 'status': 'QUEUED'})
                r = runs[0]
                if len(runs) != 1 or r['run_attempt'] != 1:
                    raise ValueError('DUPLICATE_OR_RERUN_NOT_ACCEPTED')
                state = {**job, 'status': r['status'], 'run': r['id'], 'url': r['html_url'], 'conclusion': r['conclusion']}
                if r['status'] == 'completed' and r['conclusion'] != 'success':
                    state['meaning']='CALCULATION_FAILED_OR_NOT_COMPLETED_NOT_AN_ENGINEERING_VERDICT'
                    failed=gh(f"actions/runs/{r['id']}/artifacts")['artifacts']
                    failed=[a for a in failed if a['name']==f"engineering-design-{r['id']}" and not a['expired']]
                    if len(failed)==1 and failed[0]['size_in_bytes']<=64*1024*1024:
                        content=gh(f"actions/artifacts/{failed[0]['id']}/zip",binary=True)
                        if 'sha256:'+hashlib.sha256(content).hexdigest()!=failed[0]['digest']:raise ValueError('FAILED_ARTIFACT_DIGEST')
                        store=REPO/ARTIFACT/'evidence'/str(int(r['id']));store.mkdir(parents=True,exist_ok=True)
                        archive=store/'official_failure.zip'
                        if archive.exists() and archive.read_bytes()!=content:raise ValueError('PRESERVED_FAILURE_CHANGED')
                        if not archive.exists():
                            with archive.open('xb') as f:f.write(content)
                        state['failed_evidence']='OFFICIAL_FAILURE_ZIP_PRESERVED_NO_RETRY'
                if r['status'] == 'completed' and r['conclusion'] == 'success':
                    arts = gh(f"actions/runs/{r['id']}/artifacts")['artifacts']
                    expected = f"engineering-design-{r['id']}"
                    arts = [a for a in arts if a['name'] == expected and not a['expired']]
                    if len(arts) != 1 or arts[0]['size_in_bytes'] > 64 * 1024 * 1024:
                        raise ValueError('OFFICIAL_ARTIFACT_INVENTORY')
                    data = gh(f"actions/artifacts/{arts[0]['id']}/zip", binary=True)
                    if 'sha256:' + hashlib.sha256(data).hexdigest() != arts[0]['digest']:
                        raise ValueError('OFFICIAL_ARTIFACT_DIGEST')
                    with zipfile.ZipFile(io.BytesIO(data)) as z:
                        if sum(i.file_size for i in z.infolist()) > 128 * 1024 * 1024:
                            raise ValueError('ZIP_EXPANSION_LIMIT')
                        names = z.namelist()
                        if len(set(names)) != len(names):
                            raise ValueError('DUPLICATE_ZIP_ENTRY')
                        suffix = f'{ARTIFACT}/{r["id"]}-1/baseline/'
                        def raw(name):
                            hits = [n for n in names if n.endswith(suffix + name)]
                            if len(hits) != 1:
                                raise ValueError('MISSING_BOUND_EVIDENCE_' + name)
                            return z.read(hits[0])
                        def read(name):
                            return parse(raw(name))
                        index = read('artifact_hashes.json')
                        if index['source_commit'] != job['commit'] or index['manifest_sha256'] != job['manifest_sha256']:
                            raise ValueError('SOURCE_MANIFEST_IDENTITY')
                        records = {p['path']:p for p in index['records']}
                        required = ('job_status.json','external_job_identity.json','environment_before.json','environment_after.json','result.json','delivery/research_result.json')
                        if not all(k in records for k in required):
                            raise ValueError('RAW_INDEX_INCOMPLETE')
                        for name, record in records.items():
                            content = raw(name)
                            if hashlib.sha256(content).hexdigest() != record['sha256'] or len(content) != record['bytes']:
                                raise ValueError('RAW_EVIDENCE_HASH_' + name)
                        native, proof, env = read('job_status.json'), read('external_job_identity.json'), read('environment_before.json')
                        after, result = read('environment_after.json'), read('delivery/research_result.json')
                        execution = read('result.json')
                        expected_env = parse((HERE/'resource_environment.json').read_bytes())
                        if (not native['cleanup_complete'] or native['active_after_cleanup'] != 0 or native['child_exitcode'] != 0
                            or not native['assigned_before_resume'] or not native['resumed'] or native['outcome'] != 'EXITED'
                            or not proof['in_target_job'] or proof['actual_python_pid'] != native['pid']
                            or proof['cpu_rate'] != 10000 or proof['process_mb'] != 4096 or proof['job_mb'] != 8192
                            or env != after or env['source_commit'] != job['commit'] or env['resource_policy'] != expected_env
                            or env['image'] not in expected_env['allowed_images'] or env['python'] != expected_env['python'] or env['numpy'] != expected_env['numpy']
                            or execution['status'] != 'PASS' or execution['elapsed_s'] > 480
                            or result['manifest_sha256'] != job['manifest_sha256'] or result['source_commit'] != job['commit']
                            or result['request_sha256'] != job['request_sha256'] or result['schema'] != 'C2C-RESEARCH-RESULT-1'
                            or result['engineering_status'] != 'MEMPHIS_ENGINEERING_NOT_APPROVED' or result['complete_system'] is not False
                            or result['design_sha256'] != job['design_sha256'] or result['model'] != job['model']):
                            raise ValueError('RESULT_IDENTITY_OR_CLEANUP')
                        frames=result['frames'];duration=90 if job['model']=='tank90' else 60
                        if result['physical_seconds'] != duration or len(frames) != duration+1 or [f['t_s'] for f in frames] != list(range(duration+1)):
                            raise ValueError('INCOMPLETE_SHORT_MODEL_TIMELINE')
                        evidence=REPO/ARTIFACT/'evidence'/str(int(r['id']))
                        evidence.mkdir(parents=True,exist_ok=True)
                        archive=evidence/'official.zip'
                        if archive.exists():
                            if archive.read_bytes()!=data:raise ValueError('PRESERVED_OFFICIAL_ZIP_CHANGED')
                        else:
                            with archive.open('xb') as f:f.write(data)
                        receipt=evidence/'verified_result.json'
                        if not receipt.exists():
                            with receipt.open('xb') as f:f.write(raw_json(dict(run=r['id'],commit=job['commit'],artifact_id=arts[0]['id'],official_digest=arts[0]['digest'],result=result)))
                        state['result'] = result
                        state['verification'] = 'OFFICIAL_ZIP_RAW_SOURCE_INPUT_PID_ENV_CLEANUP_VERIFIED'
                return self.reply(200, state)
            return self.reply(404, {'error': 'NOT_FOUND'})
        except (ValueError, OSError, KeyError, TypeError, zipfile.BadZipFile, subprocess.TimeoutExpired) as e:
            self.reply(422, {'error': str(e)})

    def do_POST(self):
        locked=False
        try:
            self.local(write=True)
            if self.path != '/api/jobs':
                return self.reply(404, {'error': 'NOT_FOUND'})
            length = int(self.headers.get('Content-Length', '0'))
            if length < 1 or length > 2 * 1024 * 1024:
                raise ValueError('REQUEST_SIZE')
            if self.headers.get('Content-Type','').split(';')[0] != 'application/json':
                raise ValueError('JSON_CONTENT_TYPE_REQUIRED')
            req = parse(self.rfile.read(length))
            check_request(req)
            cfg = self.server.remote
            if not cfg.get('enabled') or not re.fullmatch('[a-f0-9]{40}', cfg.get('source_commit', '')):
                return self.reply(409, {'error': 'REMOTE_AUTHORIZATION_REQUIRED：本轮专用分支提交、推送和远程开发测试尚未配置授权。可先导出请求；未执行任何模型。'})
            if not self.server.submit_lock.acquire(blocking=False):
                return self.reply(409, {'error':'SUBMISSION_IN_PROGRESS：等待当前提交回执，不重复发起。'})
            locked=True
            for existing in self.server.jobs.values():
                if existing.get('source_parent') == cfg['source_commit'] and existing['design_sha256'] == req['design_sha256'] and existing['model'] == req['model']:
                    return self.reply(200, existing)  # No duplicate dispatch or automatic failed-job retry.
            # Only data changes on a new branch. The executable source is fixed by operator configuration.
            parent = cfg['source_commit']
            source = gh('git/commits/' + parent)
            manifest = gh('contents/' + PREFIX + '/source_manifest.json?ref=' + parent)
            manifest_hash = hashlib.sha256(base64.b64decode(manifest['content'])).hexdigest()
            if manifest_hash != hashlib.sha256((HERE/'source_manifest.json').read_bytes()).hexdigest():
                raise ValueError('LOCAL_REMOTE_EXECUTABLE_IDENTITY_MISMATCH')
            request_text = json.dumps(req, ensure_ascii=False, allow_nan=False)
            blob = gh('git/blobs', {'encoding': 'utf-8', 'content': request_text})
            tree = gh('git/trees', {'base_tree': source['tree']['sha'], 'tree': [
                {'path': PREFIX + '/request.json', 'mode': '100644', 'type': 'blob', 'sha': blob['sha']}]})
            ident = uuid.uuid4().hex[:12]
            commit = gh('git/commits', {'parents': [parent], 'tree': tree['sha'], 'message': 'Bound C2C research input ' + ident})
            branch = 'codex/engineering-design-mvp-run-' + ident
            gh('git/refs', {'ref': 'refs/heads/' + branch, 'sha': commit['sha']})
            job = {'id': ident, 'branch': branch, 'commit': commit['sha'], 'source_parent':parent, 'design_sha256': req['design_sha256'], 'model': req['model'], 'status': 'SUBMITTED', 'manifest_sha256':manifest_hash,'request_sha256':hashlib.sha256(request_text.encode()).hexdigest()}
            self.server.jobs[ident] = job
            store = REPO / ARTIFACT / 'requests'
            store.mkdir(parents=True, exist_ok=True)
            (store / (ident + '.json')).write_bytes(raw_json({'job': job, 'request': req}))
            self.reply(202, job)
        except (ValueError, OSError, KeyError, TypeError, subprocess.TimeoutExpired) as e:
            self.reply(422, {'error': str(e)})
        finally:
            if locked:self.server.submit_lock.release()

    def do_PUT(self):
        self.reply(405, {'error': 'METHOD_NOT_ALLOWED'})
    do_DELETE = do_PUT
    do_PATCH = do_PUT
    do_OPTIONS = do_PUT


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--port', type=int, default=8768)
    p.add_argument('--remote-config', type=Path)
    args = p.parse_args()
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    server.remote = json.loads(args.remote_config.read_bytes()) if args.remote_config else {'enabled': False}
    server.jobs = {}
    server.submit_lock = threading.Lock()
    store = REPO / ARTIFACT / 'requests'
    for f in store.glob('*.json') if store.exists() else []:
        record = json.loads(f.read_bytes());server.jobs[record['job']['id']] = record['job']
    print(f'C2C Engineering Design: http://127.0.0.1:{args.port} (no local numerical models)', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
