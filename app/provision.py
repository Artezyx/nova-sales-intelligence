"""Aprovisionamiento local explícito; no existe registro público."""
import argparse, getpass, os
from sqlalchemy.orm import Session
from sqlalchemy import select
from .models import Base, Org, User, Lead
from .main import make_engine, PH

DEMO=[
 dict(name='Prospecto Alfa',company='Comercial Alba',stage='qualified',interactions=15,days_since_contact=2,demo_requested=True,budget_confirmed=True,decision_maker=True,fit=5,contact_allowed=True),
 dict(name='Prospecto Beta',company='Logística Norte',stage='contacted',interactions=6,days_since_contact=14,demo_requested=False,budget_confirmed=False,decision_maker=True,fit=4,contact_allowed=True),
 dict(name='Prospecto Gamma',company='Industrias Delta',stage='new',interactions=1,days_since_contact=45,demo_requested=False,budget_confirmed=False,decision_maker=False,fit=1,contact_allowed=False),
 dict(name='Prospecto Épsilon',company='Sistemas Prisma',stage='qualified',interactions=12,days_since_contact=1,demo_requested=True,budget_confirmed=True,decision_maker=False,fit=4,contact_allowed=True),
 dict(name='Prospecto Zeta',company='Grupo Horizonte',stage='won',interactions=18,days_since_contact=1,demo_requested=True,budget_confirmed=True,decision_maker=True,fit=5,contact_allowed=True),
]
def provision(engine,org,email,password,role='manager',demo=False):
    if len(password)<12 or len(password)>128: raise ValueError('La contraseña debe tener de 12 a 128 caracteres')
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        if s.scalar(select(User).where(User.email==email.lower())): raise ValueError('Correo ya registrado')
        existing=s.scalars(select(Org).where(Org.name==org)).all()
        if len(existing)>1: raise ValueError('Nombre de organización ambiguo')
        o=existing[0] if existing else Org(name=org);s.add(o);s.flush()
        u=User(org_id=o.id,email=email.lower(),password=PH.hash(password),role=role);s.add(u)
        if demo and not s.scalar(select(Lead).where(Lead.org_id==o.id).limit(1)):
            s.add_all([Lead(org_id=o.id,**d) for d in DEMO])
        s.commit()

def main():
    p=argparse.ArgumentParser();p.add_argument('--org',required=True);p.add_argument('--email',required=True);p.add_argument('--role',choices=['manager','analyst'],default='manager');p.add_argument('--demo',action='store_true');args=p.parse_args()
    password=os.getenv('NOVA_PROVISION_PASSWORD') or getpass.getpass('Contraseña: ')
    engine=make_engine(os.getenv('DATABASE_URL','sqlite:///./nova.db'));provision(engine,args.org,args.email,password,args.role,args.demo);print('Usuario creado.')
if __name__=='__main__': main()
