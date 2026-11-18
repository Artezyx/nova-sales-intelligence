from datetime import datetime,timezone,timedelta
import jwt
from conftest import SECRET

def test_health(client): assert client.get('/health').json()=={'status':'ok'}
def test_requires_login(client): assert client.get('/api/leads').status_code==401
def test_bad_login(client): assert client.post('/api/login',json={'email':'manager@alpha.example','password':'wrong'}).status_code==401
def test_bad_token(client): assert client.get('/api/leads',headers={'Authorization':'Bearer invalid'}).status_code==401
def test_expired_token(client,auth):
    raw=auth['manager']['Authorization'].split()[1];claims=jwt.decode(raw,SECRET,algorithms=['HS256'],audience='nova-api');claims['exp']=datetime.now(timezone.utc)-timedelta(seconds=1);token=jwt.encode(claims,SECRET,algorithm='HS256');assert client.get('/api/leads',headers={'Authorization':'Bearer '+token}).status_code==401
def test_create_score(lead): assert lead['score']>=70 and len(lead['factors'])==6 and lead['revision']==1
def test_input_bounds(client,auth,payload): assert client.post('/api/leads',headers=auth['manager'],json={**payload,'fit':6}).status_code==422
def test_forbid_extra(client,auth,payload): assert client.post('/api/leads',headers=auth['manager'],json={**payload,'org_id':'other'}).status_code==422
def test_isolate_list(client,auth,lead): assert lead['id'] not in [l['id'] for l in client.get('/api/leads',headers=auth['other']).json()]
def test_isolate_edit(client,auth,lead,payload): assert client.put('/api/leads/'+lead['id'],headers=auth['other'],json={**payload,'revision':1}).status_code==404
def test_isolate_assistant(client,auth,lead): assert client.post('/api/assistant',headers=auth['other'],json={'question':'presupuesto','lead_id':lead['id']}).status_code==404
def test_isolate_recommend(client,auth,lead): assert client.post('/api/leads/'+lead['id']+'/recommend',headers=auth['other']).status_code==404
def suggest(client,auth,lead):
    r=client.post('/api/leads/'+lead['id']+'/recommend',headers=auth['analyst']);assert r.status_code==201,r.text;return r.json()
def test_idempotency(client,auth,lead): assert suggest(client,auth,lead)['id']==suggest(client,auth,lead)['id']
def test_analyst_cannot_approve(client,auth,lead):
    r=suggest(client,auth,lead);assert client.post('/api/reviews/'+r['id']+'/decision',headers=auth['analyst'],json={'decision':'approved'}).status_code==403
def test_approval_creates_one_task(client,auth,lead):
    r=suggest(client,auth,lead);path='/api/reviews/'+r['id']+'/decision';assert client.post(path,headers=auth['manager'],json={'decision':'approved'}).status_code==200;assert client.post(path,headers=auth['manager'],json={'decision':'approved'}).status_code==409;ts=client.get('/api/tasks',headers=auth['manager']).json();assert sum(t['review_id']==r['id'] for t in ts)==1
    t=next(t for t in ts if t['review_id']==r['id']);assert client.patch('/api/tasks/'+t['id'],headers=auth['other'],json={'status':'done'}).status_code==404;assert client.patch('/api/tasks/'+t['id'],headers=auth['analyst'],json={'status':'done'}).json()['status']=='done'
def test_reject_no_task(client,auth,lead):
    r=suggest(client,auth,lead);assert client.post('/api/reviews/'+r['id']+'/decision',headers=auth['manager'],json={'decision':'rejected'}).status_code==200;assert all(t['review_id']!=r['id'] for t in client.get('/api/tasks',headers=auth['manager']).json())
def test_no_consent(client,auth,lead,payload):
    path='/api/leads/'+lead['id'];assert client.put(path,headers=auth['manager'],json={**payload,'contact_allowed':False,'revision':1}).status_code==200;assert client.post(path+'/recommend',headers=auth['manager']).status_code==409
def test_stale_review_and_revision(client,auth,lead,payload):
    r=suggest(client,auth,lead);path='/api/leads/'+lead['id'];assert client.put(path,headers=auth['manager'],json={**payload,'fit':4,'revision':1}).status_code==200;assert client.put(path,headers=auth['manager'],json={**payload,'revision':1}).status_code==409;assert client.post('/api/reviews/'+r['id']+'/decision',headers=auth['manager'],json={'decision':'approved'}).status_code==409;assert suggest(client,auth,lead)['id']!=r['id']
def test_revoke_cancels_tasks(client,auth,lead,payload):
    r=suggest(client,auth,lead);assert client.post('/api/reviews/'+r['id']+'/decision',headers=auth['manager'],json={'decision':'approved'}).status_code==200;t=next(t for t in client.get('/api/tasks',headers=auth['manager']).json() if t['review_id']==r['id']);assert client.put('/api/leads/'+lead['id'],headers=auth['manager'],json={**payload,'contact_allowed':False,'revision':1}).status_code==200;assert client.patch('/api/tasks/'+t['id'],headers=auth['manager'],json={'status':'open'}).status_code==409;assert next(x for x in client.get('/api/tasks',headers=auth['manager']).json() if x['id']==t['id'])['status']=='cancelled'
def test_review_isolation(client,auth,lead):
    r=suggest(client,auth,lead);assert client.post('/api/reviews/'+r['id']+'/decision',headers=auth['other'],json={'decision':'approved'}).status_code==404;assert all(x['id']!=r['id'] for x in client.get('/api/reviews',headers=auth['other']).json())
def test_assistant_grounded(client,auth,lead):
    a=client.post('/api/assistant',headers=auth['manager'],json={'question':'objeciones de precio descuento','lead_id':lead['id']}).json();assert a['sources'][0]['id']=='objeciones' and a['lead_summary']['name']==lead['name']
def test_dashboard_and_model(client,auth,lead):
    assert client.get('/api/dashboard',headers=auth['manager']).json()['total']>0;assert client.get('/api/dashboard',headers=auth['other']).json()['total']==0;assert client.get('/api/model',headers=auth['manager']).json()['data']=='synthetic'
def test_audit_permissions(client,auth,lead):
    assert client.get('/api/audit',headers=auth['analyst']).status_code==403;assert any(a['action']=='lead.created' and a['entity_id']==lead['id'] for a in client.get('/api/audit',headers=auth['manager']).json());assert client.get('/api/audit',headers=auth['other']).json()==[]
def test_security_headers(client,auth):
    assert "script-src 'self'" in client.get('/').headers['Content-Security-Policy'];assert client.get('/api/me',headers=auth['manager']).headers['Cache-Control']=='no-store'
