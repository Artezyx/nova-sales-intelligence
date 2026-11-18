import os, secrets
from datetime import datetime,timedelta,timezone
from pathlib import Path
from typing import Literal
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from sqlalchemy import create_engine, select, update, event
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import jwt
from .models import Base, Org, User, Lead, Review, Task, Audit
from .intelligence import score, answer, recommend, train

STAGES=Literal['new','contacted','qualified','won','lost']
class Strict(BaseModel): model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
class Login(Strict):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=False)
    email: EmailStr
    password: str=Field(min_length=1,max_length=128)
class LeadInput(Strict):
    name: str=Field(min_length=1,max_length=120)
    company: str=Field(min_length=1,max_length=120)
    stage: STAGES='new'
    interactions: int=Field(default=0,ge=0,le=20)
    days_since_contact: int=Field(default=0,ge=0,le=90)
    demo_requested: bool=False
    budget_confirmed: bool=False
    decision_maker: bool=False
    fit: int=Field(default=0,ge=0,le=5)
    contact_allowed: bool=False
class LeadEdit(LeadInput): revision: int=Field(ge=1)
class Question(Strict):
    question: str=Field(min_length=3,max_length=500)
    lead_id: str|None=Field(default=None,max_length=36)
class Decision(Strict): decision: Literal['approved','rejected']
class TaskEdit(Strict): status: Literal['open','done']
PH=PasswordHasher(time_cost=2,memory_cost=19456,parallelism=1)
DUMMY=PH.hash(secrets.token_hex(32))

def make_engine(url):
    engine=create_engine(url,connect_args={'check_same_thread':False} if url.startswith('sqlite') else {},pool_pre_ping=True)
    if url.startswith('sqlite'):
        @event.listens_for(engine,'connect')
        def fk(conn,rec): conn.execute('PRAGMA foreign_keys=ON')
    return engine

def fields(obj, keys): return {k:getattr(obj,k) for k in keys}
def lead_data(l): return fields(l,LeadInput.model_fields)
def lead_out(l): return {'id':l.id,'revision':l.revision,**lead_data(l),**score(lead_data(l))}
def review_out(r): return fields(r,['id','lead_id','lead_revision','recommendation','status','decided_by','created_at'])
def task_out(t): return fields(t,['id','lead_id','review_id','title','status'])

def create_app(database_url=None,secret=None):
    secret=secret or os.getenv('NOVA_SECRET','')
    if len(secret)<32: raise RuntimeError('NOVA_SECRET debe tener al menos 32 caracteres.')
    engine=make_engine(database_url or os.getenv('DATABASE_URL','sqlite:///./nova.db'))
    Base.metadata.create_all(engine)
    train()
    app=FastAPI(title='NOVA Sales Intelligence',version='1.0.0')
    app.state.engine=engine
    bearer=HTTPBearer(auto_error=False)
    def db():
        with Session(engine) as s: yield s
    def current(credentials: HTTPAuthorizationCredentials|None=Depends(bearer),s:Session=Depends(db)):
        try:
            if not credentials: raise ValueError()
            claims=jwt.decode(credentials.credentials,secret,algorithms=['HS256'],issuer='nova',audience='nova-api',options={'require':['exp','iat','sub','iss','aud']})
            u=s.get(User,claims['sub'])
            if not u: raise ValueError()
            return u
        except (jwt.PyJWTError,ValueError,TypeError): raise HTTPException(401,'Credenciales inválidas',headers={'WWW-Authenticate':'Bearer'})
    def manager(u:User=Depends(current)):
        if u.role!='manager': raise HTTPException(403,'Se requiere un responsable comercial')
        return u
    def scoped(s,model,id,u):
        obj=s.scalar(select(model).where(model.id==id,model.org_id==u.org_id))
        if not obj: raise HTTPException(404,'Registro no encontrado')
        return obj
    def audit(s,u,action,id): s.add(Audit(org_id=u.org_id,actor_id=u.id,action=action,entity_id=id))
    @app.middleware('http')
    async def headers(request, call_next):
        response=await call_next(request)
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['X-Frame-Options']='DENY'
        response.headers['Referrer-Policy']='no-referrer'
        if request.url.path.startswith('/api/'): response.headers['Cache-Control']='no-store'
        if request.url.path=='/' or request.url.path.startswith('/static'):
            response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
        return response
    @app.get('/health')
    def health(): return {'status':'ok'}
    @app.post('/api/login')
    def login(data:Login,s:Session=Depends(db)):
        u=s.scalar(select(User).where(User.email==data.email.lower()))
        try: PH.verify(u.password if u else DUMMY,data.password)
        except VerificationError: raise HTTPException(401,'Credenciales inválidas')
        if not u: raise HTTPException(401,'Credenciales inválidas')
        now=datetime.now(timezone.utc)
        return {'access_token':jwt.encode({'sub':u.id,'iat':now,'exp':now+timedelta(minutes=60),'iss':'nova','aud':'nova-api'},secret,algorithm='HS256'),'role':u.role,'email':u.email}
    @app.get('/api/me')
    def me(u:User=Depends(current)): return fields(u,['email','role','org_id'])
    @app.get('/api/model')
    def model(u:User=Depends(current)): return train()[1]
    @app.get('/api/leads')
    def list_leads(limit:int=Query(100,ge=1,le=200),offset:int=Query(0,ge=0),u:User=Depends(current),s:Session=Depends(db)):
        rows=s.scalars(select(Lead).where(Lead.org_id==u.org_id).order_by(Lead.created_at.desc(),Lead.id).offset(offset).limit(limit)).all()
        return [lead_out(l) for l in rows]
    @app.post('/api/leads',status_code=201)
    def add(data:LeadInput,u:User=Depends(current),s:Session=Depends(db)):
        l=Lead(org_id=u.org_id,**data.model_dump());s.add(l);s.flush();audit(s,u,'lead.created',l.id);s.commit();return lead_out(l)
    @app.put('/api/leads/{id}')
    def edit(id:str,data:LeadEdit,u:User=Depends(current),s:Session=Depends(db)):
        l=scoped(s,Lead,id,u)
        changed=s.execute(update(Lead).where(Lead.id==id,Lead.org_id==u.org_id,Lead.revision==data.revision).values(**data.model_dump(exclude={'revision'}),revision=data.revision+1))
        if changed.rowcount!=1: raise HTTPException(409,'Registro actualizado; recarga antes de editar')
        # Una edición invalida sugerencias pendientes de la versión anterior.
        s.execute(update(Review).where(Review.lead_id==id,Review.org_id==u.org_id,Review.status=='pending').values(status='stale'))
        # Si se retira consentimiento o se cierra el prospecto, se cancelan tareas abiertas.
        if not data.contact_allowed or data.stage in ('won','lost'):
            s.execute(update(Task).where(Task.lead_id==id,Task.org_id==u.org_id,Task.status=='open').values(status='cancelled'))
        audit(s,u,'lead.updated',id);s.commit();s.refresh(l);return lead_out(l)
    @app.get('/api/dashboard')
    def dashboard(u:User=Depends(current),s:Session=Depends(db)):
        leads=s.scalars(select(Lead).where(Lead.org_id==u.org_id)).all()
        active=[l for l in leads if l.stage not in ('won','lost')]
        high=sum(score(lead_data(l))['priority']=='alta' for l in active)
        reviews=s.scalars(select(Review).where(Review.org_id==u.org_id,Review.status=='pending')).all()
        tasks=s.scalars(select(Task).where(Task.org_id==u.org_id,Task.status=='open')).all()
        return {'total':len(leads),'high_priority':high,'pending_reviews':len(reviews),'open_tasks':len(tasks),'stages':{k:sum(l.stage==k for l in leads) for k in ['new','contacted','qualified','won','lost']}}
    @app.post('/api/leads/{id}/recommend',status_code=201)
    def suggestion(id:str,u:User=Depends(current),s:Session=Depends(db)):
        l=s.scalar(select(Lead).where(Lead.id==id,Lead.org_id==u.org_id).with_for_update())
        if not l: raise HTTPException(404,'Registro no encontrado')
        recommendation=recommend(lead_data(l))
        if not recommendation: raise HTTPException(409,'Prospecto cerrado o sin permiso de contacto')
        existing=s.scalar(select(Review).where(Review.lead_id==id,Review.lead_revision==l.revision))
        if existing: return review_out(existing)
        r=Review(org_id=u.org_id,lead_id=id,lead_revision=l.revision,recommendation=recommendation);s.add(r)
        try: s.flush();audit(s,u,'review.created',r.id);s.commit()
        except IntegrityError:
            s.rollback();r=s.scalar(select(Review).where(Review.lead_id==id,Review.lead_revision==l.revision));
            if not r: raise
        return review_out(r)
    @app.get('/api/reviews')
    def reviews(u:User=Depends(current),s:Session=Depends(db)):
        return [review_out(r) for r in s.scalars(select(Review).where(Review.org_id==u.org_id).order_by(Review.created_at.desc()).limit(200))]
    @app.post('/api/reviews/{id}/decision')
    def decision(id:str,data:Decision,u:User=Depends(manager),s:Session=Depends(db)):
        r=scoped(s,Review,id,u)
        # Serializar ediciones/decisiones sobre el mismo lead en PostgreSQL; SQLite escribe secuencialmente.
        l=s.scalar(select(Lead).where(Lead.id==r.lead_id,Lead.org_id==u.org_id).with_for_update())
        if r.status!='pending' or not l or l.revision!=r.lead_revision or not recommend(lead_data(l)): raise HTTPException(409,'Revisión no vigente')
        result=s.execute(update(Review).where(Review.id==id,Review.org_id==u.org_id,Review.status=='pending').values(status=data.decision,decided_by=u.id))
        if result.rowcount!=1: raise HTTPException(409,'Revisión ya procesada')
        if data.decision=='approved': s.add(Task(org_id=u.org_id,lead_id=l.id,review_id=r.id,title=r.recommendation))
        audit(s,u,'review.'+data.decision,id);s.commit();s.refresh(r);return review_out(r)
    @app.get('/api/tasks')
    def tasks(u:User=Depends(current),s:Session=Depends(db)):
        return [task_out(t) for t in s.scalars(select(Task).where(Task.org_id==u.org_id).limit(200))]
    @app.patch('/api/tasks/{id}')
    def task_edit(id:str,data:TaskEdit,u:User=Depends(current),s:Session=Depends(db)):
        t=scoped(s,Task,id,u)
        l=s.scalar(select(Lead).where(Lead.id==t.lead_id,Lead.org_id==u.org_id).with_for_update())
        s.refresh(t)
        if t.status=='cancelled' or (data.status=='open' and (not l or not recommend(lead_data(l)))): raise HTTPException(409,'Tarea cancelada o prospecto no elegible')
        t.status=data.status;audit(s,u,'task.'+data.status,id);s.commit();return task_out(t)
    @app.post('/api/assistant')
    def assistant(data:Question,u:User=Depends(current),s:Session=Depends(db)):
        lead=lead_data(scoped(s,Lead,data.lead_id,u)) if data.lead_id else None
        return answer(data.question,lead)
    @app.get('/api/audit')
    def audits(u:User=Depends(manager),s:Session=Depends(db)):
        return [fields(a,['id','action','entity_id','actor_id','created_at']) for a in s.scalars(select(Audit).where(Audit.org_id==u.org_id).order_by(Audit.created_at.desc()).limit(200))]
    static=Path(__file__).parent/'static';app.mount('/static',StaticFiles(directory=static),name='static')
    @app.get('/',include_in_schema=False)
    def index(): return FileResponse(static/'index.html')
    return app
