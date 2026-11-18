"""Modelo didáctico: entrenamiento sintético reproducible, no predicción comercial validada."""
from functools import lru_cache
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, brier_score_loss, accuracy_score
from sklearn.feature_extraction.text import TfidfVectorizer

VERSION = 'synthetic-logit-v1'
FEATURES = ('interactions', 'days_since_contact', 'demo_requested', 'budget_confirmed', 'decision_maker', 'fit')
LABELS = ('Interacciones recientes', 'Recencia del contacto', 'Demostración solicitada', 'Presupuesto confirmado', 'Contacto decisor', 'Ajuste al producto')
SCALES = np.array([20., 90., 1., 1., 1., 5.])

def vector(record):
    return np.array([float(record[k]) for k in FEATURES]) / SCALES

@lru_cache(maxsize=1)
def train():
    rng = np.random.default_rng(42)
    n = 3200
    raw = np.column_stack([rng.integers(0,21,n), rng.integers(0,91,n), rng.integers(0,2,(n,3)), rng.integers(0,6,n)])
    x = raw / SCALES
    # Etiquetas simuladas a partir de una hipótesis explícita; no se usan datos de clientes.
    logits = -2.5 + x @ np.array([1.5,-1.5,1.2,1.4,.8,1.7])
    y = rng.binomial(1, 1/(1+np.exp(-logits)))
    a,b,c,d = train_test_split(x,y,test_size=.25,random_state=42,stratify=y)
    model = LogisticRegression(random_state=42, max_iter=1000).fit(a,c)
    p = model.predict_proba(b)[:,1]
    return model, {'version':VERSION,'data':'synthetic','train_rows':len(a),'test_rows':len(b),'roc_auc':round(float(roc_auc_score(d,p)),4),'brier':round(float(brier_score_loss(d,p)),4),'accuracy_at_0_5':round(float(accuracy_score(d,p>=.5)),4),'warning':'Métricas sobre datos sintéticos; no prueban eficacia en ventas reales.'}

def score(record):
    model,_ = train()
    x=vector(record)
    prob=float(model.predict_proba(x.reshape(1,-1))[0,1])
    # Aportes al logit respecto del punto de referencia medio 0.5, no causalidad.
    factors=[{'feature':k,'label':label,'contribution':round(float(v),3)} for k,label,v in zip(FEATURES,LABELS,model.coef_[0]*(x-.5))]
    points=round(prob*100)
    return {'score':points,'priority':'alta' if points>=70 else 'media' if points>=40 else 'baja','version':VERSION,'factors':sorted(factors,key=lambda f:abs(f['contribution']),reverse=True),'disclaimer':'Índice experimental entrenado con datos sintéticos; no es una probabilidad de cierre validada.'}

KNOWLEDGE = [
 ('calificacion','Calificación de prospectos','Confirma necesidad, presupuesto, autoridad y plazo. Registra evidencias en el CRM; no supongas información que no fue confirmada.','calificar prospecto scoring prioridad presupuesto decisor necesidad fit'),
 ('seguimiento','Seguimiento comercial','Después de una demo, resume acuerdos y confirma el siguiente paso. Si no hay respuesta, programa un recordatorio y respeta preferencias de contacto.','seguimiento contactar llamada correo respuesta demo reunión actividad'),
 ('objeciones','Objeciones de precio','Pregunta por el presupuesto y las necesidades. Explica valor con ejemplos verificables; evita prometer descuentos o condiciones no autorizadas.','precio costo caro descuento objecion presupuesto negociación'),
 ('privacidad','Privacidad y consentimiento','Usa únicamente información comercial necesaria. Respeta el consentimiento y las solicitudes de no contacto. No envíes mensajes sin autorización.','privacidad datos consentimiento eliminar contacto spam seguridad'),
 ('pipeline','Gestión del pipeline','Actualiza la etapa cuando haya evidencia. Separa oportunidades ganadas y perdidas; registra el motivo y el siguiente paso.','pipeline ventas oportunidad etapa cerrar ganado perdido reporte')]

@lru_cache(maxsize=1)
def retriever():
    v=TfidfVectorizer(strip_accents='unicode',ngram_range=(1,2),sublinear_tf=True)
    return v,v.fit_transform([f'{title} {body} {tags}' for _,title,body,tags in KNOWLEDGE])

def answer(question, lead=None):
    v, matrix=retriever(); similarities=(matrix @ v.transform([question]).T).toarray().ravel()
    i=int(np.argmax(similarities)); result={'mode':'retrieval_local','answer':'No encontré una guía pertinente. Reformula la pregunta o consulta a tu responsable comercial.','sources':[],'lead_summary':None}
    if similarities[i]>=.12:
        key,title,body,_=KNOWLEDGE[i]; result.update(answer=body,sources=[{'id':key,'title':title}])
    if lead is not None:
        result['lead_summary']={'name':lead['name'],'stage':lead['stage'],'score':score(lead)['score'],'note':'Información registrada en NOVA; requiere validación humana.'}
    return result

def recommend(lead):
    if lead['stage'] in ('won','lost') or not lead['contact_allowed']:
        return None
    if not lead['budget_confirmed']:
        return 'Confirmar presupuesto y necesidad con el prospecto.'
    if lead['demo_requested']:
        return 'Coordinar la demostración y confirmar el siguiente paso.'
    if lead['days_since_contact']>=7:
        return 'Revisar el seguimiento pendiente y confirmar interés.'
    if score(lead)['priority']=='alta':
        return 'Preparar propuesta comercial para revisión humana.'
    return 'Verificar criterios de calificación antes de avanzar.'
