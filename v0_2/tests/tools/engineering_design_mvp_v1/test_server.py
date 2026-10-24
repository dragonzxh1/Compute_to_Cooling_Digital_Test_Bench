"""Local HTTP/contract tests only. Never import or execute the numerical adapter."""
import ast
import hashlib
import http.client
import io
import json
import threading
import unittest
import zipfile
from pathlib import Path
from . import server
from .request_contract import check_request, parse

HERE=Path(__file__).resolve().parent


class ContractTests(unittest.TestCase):
    def request(self):
        text=(HERE/'data/baseline.json').read_text(encoding='utf-8')
        return dict(schema='C2C-ENGINEERING-JOB-1',model='tank90',design_json=text,design_sha256=hashlib.sha256(text.encode()).hexdigest())

    def test_baseline(self):
        self.assertEqual(check_request(self.request())['parameters']['tank_volume']['value'],15)

    def test_tampered_input(self):
        r=self.request();r['design_json']+=' '
        with self.assertRaisesRegex(ValueError,'HASH'):check_request(r)

    def test_unknown_model(self):
        r=self.request();r['model']='arbitrary_script'
        with self.assertRaisesRegex(ValueError,'UNREGISTERED'):check_request(r)

    def test_nonfinite_duplicate(self):
        for s in ('{"a":NaN}','{"a":1,"a":2}'):
            with self.assertRaises(ValueError):parse(s)

    def test_bad_range_and_limits(self):
        for key in ('limits','range'):
            r=self.request();d=json.loads(r['design_json'])
            if key=='limits':d['requirements']['rack_inlet_max_c']=46
            else:d['parameters']['pump_speed']['value']=2
            r['design_json']=json.dumps(d);r['design_sha256']=hashlib.sha256(r['design_json'].encode()).hexdigest()
            with self.assertRaises(ValueError):check_request(r)

    def test_python_syntax_without_model_import(self):
        for f in HERE.glob('*.py'):ast.parse(f.read_text(encoding='utf-8'),filename=str(f))


class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.http=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
        cls.http.remote={'enabled':False};cls.http.jobs={}
        cls.thread=threading.Thread(target=cls.http.serve_forever,daemon=True);cls.thread.start()
        cls.original=server.gh
        server.gh=lambda *a,**k: (_ for _ in ()).throw(AssertionError('NO_GITHUB_CALL_ALLOWED'))

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown();cls.http.server_close();server.gh=cls.original

    def call(self,path,method='GET',body=None,origin=True,host=None):
        c=http.client.HTTPConnection('127.0.0.1',self.http.server_port,timeout=3)
        headers={'Content-Type':'application/json'}
        if origin:headers['Origin']='http://127.0.0.1:'+str(self.http.server_port)
        if host:headers['Host']=host
        c.request(method,path,body=body,headers=headers);r=c.getresponse();data=r.read();c.close();return r.status,data

    def test_catalog_disabled(self):
        code,body=self.call('/api/catalog');self.assertEqual(code,200);self.assertFalse(json.loads(body)['remote_enabled'])

    def test_visual_assets_bound_and_allowlisted(self):
        _,body=self.call('/api/catalog');hashes=json.loads(body)['hashes']
        for name in ('visual-core.mjs','visual-ui.mjs','data/single_history.json','data/switching.json'):
            code,raw=self.call('/'+name);self.assertEqual(code,200)
            self.assertEqual(hashlib.sha256(raw).hexdigest(),hashes[name])

    def test_remote_not_authorized_no_github(self):
        req=ContractTests().request();code,body=self.call('/api/jobs','POST',json.dumps(req))
        self.assertEqual(code,409);self.assertIn('REMOTE_AUTHORIZATION_REQUIRED',body.decode())

    def test_origin_required(self):
        self.assertEqual(self.call('/api/jobs','POST','{}',origin=False)[0],422)

    def test_bad_host(self):
        self.assertEqual(self.call('/api/catalog',host='evil.invalid')[0],422)

    def test_no_arbitrary_path_or_command(self):
        self.assertEqual(self.call('/../AGENTS.md')[0],404)
        self.assertEqual(self.call('/api/exec','POST','{}')[0],404)

    def test_unknown_job_and_mutation_method(self):
        self.assertEqual(self.call('/api/jobs/000000000000')[0],422)
        self.assertEqual(self.call('/api/jobs','PUT','{}')[0],405)

    def synthetic_artifact(self, mode):
        # Negative admission fixtures only; no physical values or usable result curves.
        job=dict(id='f'*12,branch='synthetic-unit-test',commit='a'*40,design_sha256='b'*64,model='tank90',manifest_sha256='c'*64,request_sha256='d'*64)
        env=dict(source_commit=job['commit'],resource_policy=json.loads((HERE/'resource_environment.json').read_bytes()),image='20261021.343.1',python='3.11.9',numpy='2.4.6')
        files={'job_status.json':dict(cleanup_complete=True,active_after_cleanup=0,child_exitcode=0,assigned_before_resume=True,resumed=True,outcome='EXITED',pid=123),
               'external_job_identity.json':dict(in_target_job=True,actual_python_pid=123,cpu_rate=10000,process_mb=4096,job_mb=8192),
               'environment_before.json':env,'environment_after.json':env,'result.json':dict(status='PASS',elapsed_s=1),
               'delivery/research_result.json':dict(schema='C2C-RESEARCH-RESULT-1',design_sha256='WRONG_VERSION',model='tank90',manifest_sha256=job['manifest_sha256'],source_commit=job['commit'],request_sha256=job['request_sha256'],engineering_status='MEMPHIS_ENGINEERING_NOT_APPROVED',complete_system=False)}
        raw={k:json.dumps(v).encode() for k,v in files.items()}
        raw['artifact_hashes.json']=json.dumps(dict(source_commit=job['commit'],manifest_sha256=job['manifest_sha256'],records=[dict(path=k,sha256=hashlib.sha256(v).hexdigest(),bytes=len(v)) for k,v in raw.items()])).encode()
        if mode=='missing':raw={}
        stream=io.BytesIO()
        with zipfile.ZipFile(stream,'w') as z:
            for k,v in raw.items():z.writestr('artifacts/engineering-design-mvp-v1/123-1/baseline/'+k,v)
        data=stream.getvalue();self.http.jobs[job['id']]=job
        previous=server.gh;self.addCleanup(setattr,server,'gh',previous)
        def fake(endpoint,payload=None,binary=False):
            if endpoint.startswith('actions/runs?'):return {'workflow_runs':[dict(head_sha=job['commit'],path='.github/workflows/engineering-design-mvp-v1.yml',run_attempt=1,status='completed',id=123,html_url='about:blank',conclusion='success')]}
            if endpoint=='actions/runs/123/artifacts':return {'artifacts':[dict(id=999,name='engineering-design-123',expired=False,size_in_bytes=len(data),digest='sha256:'+('0'*64 if mode=='tamper' else hashlib.sha256(data).hexdigest()))]}
            if endpoint=='actions/artifacts/999/zip':return data
            raise AssertionError('UNEXPECTED_SYNTHETIC_ENDPOINT')
        server.gh=fake
        return self.call('/api/jobs/'+job['id'])

    def test_tampered_official_zip_rejected(self):
        code,body=self.synthetic_artifact('tamper');self.assertEqual(code,422);self.assertIn(b'OFFICIAL_ARTIFACT_DIGEST',body)

    def test_missing_evidence_rejected(self):
        code,body=self.synthetic_artifact('missing');self.assertEqual(code,422);self.assertIn(b'MISSING_BOUND_EVIDENCE',body)

    def test_cross_version_result_rejected(self):
        code,body=self.synthetic_artifact('cross-version');self.assertEqual(code,422);self.assertIn(b'RESULT_IDENTITY_OR_CLEANUP',body)


if __name__=='__main__':unittest.main(verbosity=2)
