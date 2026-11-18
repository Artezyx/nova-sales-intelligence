from app.intelligence import score,train,answer,recommend
LOW=dict(interactions=0,days_since_contact=90,demo_requested=False,budget_confirmed=False,decision_maker=False,fit=0,contact_allowed=True,stage='new')
HIGH=dict(interactions=20,days_since_contact=0,demo_requested=True,budget_confirmed=True,decision_maker=True,fit=5,contact_allowed=True,stage='qualified')
def test_reproducible(): assert score(HIGH)==score(HIGH)
def test_order(): assert score(HIGH)['score']>score(LOW)['score']
def test_metrics(): assert train()[1]['test_rows']==800 and .65<train()[1]['roc_auc']<1
def test_explanations(): assert len(score(HIGH)['factors'])==6 and all('contribution' in f for f in score(HIGH)['factors'])
def test_unknown_question(): assert answer('zxqvw zzyyx')['sources']==[]
def test_privacy_retrieval(): assert answer('privacidad consentimiento datos')['sources'][0]['id']=='privacidad'
def test_closed_or_no_consent(): assert recommend({**HIGH,'stage':'won'}) is None and recommend({**HIGH,'contact_allowed':False}) is None
def test_recommend_budget(): assert 'presupuesto' in recommend(LOW)
