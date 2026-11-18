import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.provision import provision
SECRET='test-only-secret-long-enough-123456789'
PASS='demo-test-password-12345'
@pytest.fixture(scope='module')
def application(tmp_path_factory):
    db=tmp_path_factory.mktemp('db')/'test.db';app=create_app('sqlite:///'+str(db),SECRET)
    for org,email,role in [('Alpha','manager@alpha.example','manager'),('Alpha','analyst@alpha.example','analyst'),('Beta','manager@beta.example','manager')]: provision(app.state.engine,org,email,PASS,role)
    yield app
    app.state.engine.dispose()
@pytest.fixture(scope='module')
def client(application):
    with TestClient(application) as c: yield c
@pytest.fixture(scope='module')
def auth(client):
    def get(email):
        r=client.post('/api/login',json={'email':email,'password':PASS});assert r.status_code==200,r.text;return {'Authorization':'Bearer '+r.json()['access_token']}
    return {k:get(v) for k,v in [('manager','manager@alpha.example'),('analyst','analyst@alpha.example'),('other','manager@beta.example')]}
@pytest.fixture
def payload(): return {'name':'Prospecto Demo','company':'Empresa Demo','stage':'qualified','interactions':16,'days_since_contact':2,'fit':5,'demo_requested':True,'budget_confirmed':True,'decision_maker':True,'contact_allowed':True}
@pytest.fixture
def lead(client,auth,payload):
    r=client.post('/api/leads',json=payload,headers=auth['manager']);assert r.status_code==201,r.text;return r.json()
