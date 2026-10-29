import io, os, json, secrets, hashlib
from datetime import datetime, timezone, timedelta
from typing import Annotated, Literal
from fastapi import FastAPI, Depends, Response, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import select, delete, func
from sqlalchemy.orm import Session
from .db import get_db
from .models import User, Project, Membership, HardwareProfile, Consent, Conversation, AuditEvent, LoginThrottle, Session as LoginSession, now
from .security import password_hash, password_valid, current_user, csrf_guard, auth_origin, issue, clear, valid_session

app = FastAPI(title='RoboLN v2 API', version='2.0.0-phase01', docs_url='/api/docs', openapi_url='/api/openapi.json')

class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
class Registration(Credentials):
    full_name: str = Field(min_length=1, max_length=100)
    @field_validator('full_name')
    @classmethod
    def valid_full_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError('Full name cannot be blank')
        return value.strip()
class ProfileEdit(BaseModel):
    full_name: str = Field(min_length=1, max_length=100)
    @field_validator('full_name')
    @classmethod
    def valid_full_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError('Full name cannot be blank')
        return value.strip()
class ThemeEdit(BaseModel):
    theme: Literal['light','dark','system']
class ProjectCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: str = Field(default='', max_length=2000)
    goal: str = Field(default='', max_length=1000)
    @field_validator('name')
    @classmethod
    def strip(cls,v):
        if not v.strip(): raise ValueError('Project name required')
        return v.strip()
class ProjectEdit(BaseModel):
    name: str = Field(min_length=2,max_length=100)
    description: str = Field(default='',max_length=2000)
    goal: str = Field(default='',max_length=1000)
    @field_validator('name')
    @classmethod
    def valid_project_name(cls, value: str) -> str:
        if len(value.strip()) < 2:
            raise ValueError('Project name must have at least two visible characters')
        return value.strip()
class MembershipEdit(BaseModel):
    email: EmailStr
    role: Literal['editor','viewer']
class HardwareEdit(BaseModel):
    device_class: Literal['MCU','SBC','OTHER'] = 'OTHER'
    board_model: str = Field(default='',max_length=160)
    board_revision: str = Field(default='',max_length=100)
    pin_map: dict[str,str] = Field(default_factory=dict)
    sensor_inventory: list[dict] = Field(default_factory=list, max_length=100)
    @field_validator('pin_map')
    @classmethod
    def bounded_pin_map(cls, value: dict[str,str]) -> dict[str,str]:
        if len(value)>100 or any(len(key)>80 or len(pin)>160 for key,pin in value.items()):
            raise ValueError('Pin map exceeds allowed size')
        return value
class ConsentEdit(BaseModel):
    enabled: bool
class DraftEdit(BaseModel):
    draft: str = Field(max_length=8000)

@app.get('/api/health')
def health(): return {'service':'RoboLN','status':'available','phase':'01','ai_provider':'NOT_CONFIGURED','telemetry':'NOT_IMPLEMENTED'}

def audit(db, action, user=None, project_id=None):
    db.add(AuditEvent(action=action,actor_id=user, project_id=project_id))

def user_info(u:User): return {'id':u.id,'email':u.email,'full_name':u.full_name,'theme':u.theme}

def project_info(p:Project, role):
    return {'id':p.id,'name':p.name,'description':p.description,'goal':p.goal,'role':role,'archived':p.archived,'context_version':p.context_version,'created_at':p.created_at.isoformat()}

def authorized(db:Session, pid:str, user:User, write:bool=False, owner:bool=False):
    membership=db.get(Membership,(pid,user.id))
    if not membership: raise HTTPException(404,'Project not found')
    project=db.get(Project,pid)
    if not project: raise HTTPException(404,'Project not found')
    if owner and membership.role!='owner': raise HTTPException(403,'Owner access required')
    if write and project.archived: raise HTTPException(409,'Restore archived project before editing')
    if write and membership.role not in ('owner','editor'): raise HTTPException(403,'Editor access required')
    return project, membership.role

@app.post('/api/auth/register',status_code=201,dependencies=[Depends(auth_origin)])
def register(payload:Registration, response:Response, db:Session=Depends(get_db)):
    email=str(payload.email).lower()
    if db.scalar(select(User).where(User.email==email)): raise HTTPException(409,'Email already registered')
    u=User(email=email,full_name=payload.full_name.strip(),password_hash=password_hash(payload.password))
    db.add(u);db.flush();audit(db,'user.register',u.id); db.commit()
    issue(db,response,u)
    return user_info(u)

@app.post('/api/auth/login',dependencies=[Depends(auth_origin)])
def login(payload:Credentials,response:Response,request:Request,db:Session=Depends(get_db)):
    email=str(payload.email).lower()
    client_host=request.client.host if request.client else 'unknown'
    throttle_key=hashlib.sha256((email+'|'+client_host).encode()).hexdigest()
    t=db.get(LoginThrottle,throttle_key)
    if t and t.blocked_until and t.blocked_until.replace(tzinfo=timezone.utc)>now():
        raise HTTPException(429,'Too many failed logins. Try again later.')
    u=db.scalar(select(User).where(User.email==email))
    if not u or not password_valid(u.password_hash,payload.password):
        if not t:t=LoginThrottle(key=throttle_key,failures=0);db.add(t)
        if t.last_failure and t.last_failure.replace(tzinfo=timezone.utc) < now()-timedelta(minutes=15):t.failures=0
        t.failures+=1;t.last_failure=now()
        if t.failures>=5:t.blocked_until=now()+timedelta(minutes=15)
        db.commit()
        raise HTTPException(401,'Invalid credentials')
    if t:db.delete(t);db.commit()
    issue(db,response,u)
    audit(db,'user.login',u.id);db.commit()
    return user_info(u)

@app.get('/api/auth/me')
def me(u:User=Depends(current_user)): return user_info(u)

@app.post('/api/auth/logout',dependencies=[Depends(csrf_guard)])
def logout(request:Request,response:Response,db:Session=Depends(get_db),u:User=Depends(current_user)):
    s=valid_session(request.cookies.get('roboln_session'),db)
    if s: s.revoked=True
    audit(db,'user.logout',u.id);db.commit();clear(response)
    return {'ok':True}

@app.patch('/api/profile',dependencies=[Depends(csrf_guard)])
def change_profile(payload:ProfileEdit, db:Session=Depends(get_db),u:User=Depends(current_user)):
    u.full_name=payload.full_name.strip();audit(db,'user.profile',u.id);db.commit();return user_info(u)

@app.patch('/api/preferences/theme',dependencies=[Depends(csrf_guard)])
def change_theme(payload:ThemeEdit, db:Session=Depends(get_db),u:User=Depends(current_user)):
    u.theme=payload.theme;audit(db,'user.theme',u.id);db.commit();return user_info(u)

@app.get('/api/consents')
def list_consents(db:Session=Depends(get_db),u:User=Depends(current_user)):
    return {c.kind:c.enabled for c in db.scalars(select(Consent).where(Consent.user_id==u.id))}

@app.put('/api/consents/{kind}', dependencies=[Depends(csrf_guard)])
def set_consent(kind:Literal['camera','microphone','cloud_ai','notifications'],payload:ConsentEdit,db:Session=Depends(get_db),u:User=Depends(current_user)):
    c=db.get(Consent,(u.id,kind))
    if not c: c=Consent(user_id=u.id,kind=kind);db.add(c)
    c.enabled=payload.enabled;c.updated_at=now();audit(db,'consent.'+kind,u.id);db.commit();return {'kind':kind,'enabled':c.enabled}

@app.get('/api/projects')
def list_projects(db:Session=Depends(get_db),u:User=Depends(current_user)):
    rows=db.execute(select(Project,Membership.role).join(Membership,Project.id==Membership.project_id).where(Membership.user_id==u.id).order_by(Project.created_at.desc())).all()
    return [project_info(p,role) for p,role in rows]

@app.post('/api/projects',status_code=201,dependencies=[Depends(csrf_guard)])
def create_project(payload:ProjectCreate, db:Session=Depends(get_db),u:User=Depends(current_user)):
    p=Project(name=payload.name,description=payload.description,goal=payload.goal,owner_id=u.id)
    db.add(p);db.flush();db.add(Membership(project_id=p.id,user_id=u.id,role='owner'))
    audit(db,'project.create',u.id,p.id);db.commit();return project_info(p,'owner')

@app.get('/api/projects/{pid}')
def get_project(pid:str,db:Session=Depends(get_db),u:User=Depends(current_user)):
    p,role=authorized(db,pid,u);return project_info(p,role)

@app.patch('/api/projects/{pid}',dependencies=[Depends(csrf_guard)])
def edit_project(pid:str,payload:ProjectEdit,db:Session=Depends(get_db),u:User=Depends(current_user)):
    p,role=authorized(db,pid,u,write=True)
    p.name=payload.name.strip();p.description=payload.description;p.goal=payload.goal;p.context_version+=1
    audit(db,'project.edit',u.id,pid);db.commit();return project_info(p,role)

@app.post('/api/projects/{pid}/archive',dependencies=[Depends(csrf_guard)])
def archive_project(pid:str,db:Session=Depends(get_db),u:User=Depends(current_user)):
    p,role=authorized(db,pid,u,owner=True);p.archived=not p.archived;audit(db,'project.restore' if not p.archived else 'project.archive',u.id,pid);db.commit();return project_info(p,role)

@app.delete('/api/projects/{pid}',dependencies=[Depends(csrf_guard)],status_code=204)
def delete_project(pid:str,db:Session=Depends(get_db),u:User=Depends(current_user)):
    p,_=authorized(db,pid,u,owner=True);db.delete(p);audit(db,'project.delete',u.id,pid);db.commit()

@app.get('/api/projects/{pid}/members')
def members(pid:str,db:Session=Depends(get_db),u:User=Depends(current_user)):
    authorized(db,pid,u)
    rows=db.execute(select(User,Membership.role).join(Membership,User.id==Membership.user_id).where(Membership.project_id==pid)).all()
    return [{'id':m.id,'email':m.email,'full_name':m.full_name,'role':role} for m,role in rows]

@app.put('/api/projects/{pid}/members',dependencies=[Depends(csrf_guard)])
def add_member(pid:str,payload:MembershipEdit,db:Session=Depends(get_db),u:User=Depends(current_user)):
    authorized(db,pid,u,owner=True)
    target=db.scalar(select(User).where(User.email==str(payload.email).lower()))
    if not target: raise HTTPException(404,'Invitee must first create a RoboLN account')
    existing=db.get(Membership,(pid,target.id))
    if existing and existing.role=='owner': raise HTTPException(403,'Cannot change owner')
    if existing: existing.role=payload.role
    else: db.add(Membership(project_id=pid,user_id=target.id,role=payload.role))
    audit(db,'project.member.set',u.id,pid);db.commit();return {'id':target.id,'role':payload.role}

@app.delete('/api/projects/{pid}/members/{member_id}',dependencies=[Depends(csrf_guard)])
def remove_member(pid:str,member_id:str,db:Session=Depends(get_db),u:User=Depends(current_user)):
    authorized(db,pid,u,owner=True)
    member=db.get(Membership,(pid,member_id))
    if not member: raise HTTPException(404,'Member not found')
    if member.role=='owner': raise HTTPException(403,'Cannot remove project owner')
    db.delete(member);audit(db,'project.member.remove',u.id,pid);db.commit();return {'ok':True}

@app.get('/api/projects/{pid}/hardware')
def get_hardware(pid:str,db:Session=Depends(get_db),u:User=Depends(current_user)):
    authorized(db,pid,u)
    hp=db.scalar(select(HardwareProfile).where(HardwareProfile.project_id==pid))
    return {'id':hp.id,'board_model':hp.board_model,'board_revision':hp.board_revision,'device_class':hp.device_class,'profile_review_state':hp.profile_review_state,'pin_map':hp.pin_map,'sensor_inventory':hp.sensor_inventory} if hp else None

@app.put('/api/projects/{pid}/hardware',dependencies=[Depends(csrf_guard)])
def save_hardware(pid:str,payload:HardwareEdit,db:Session=Depends(get_db),u:User=Depends(current_user)):
    p,_=authorized(db,pid,u,write=True)
    hp=db.scalar(select(HardwareProfile).where(HardwareProfile.project_id==pid))
    if not hp:hp=HardwareProfile(project_id=pid);db.add(hp)
    hp.board_model=payload.board_model.strip();hp.board_revision=payload.board_revision.strip();hp.device_class=payload.device_class
    hp.pin_map=payload.pin_map;hp.sensor_inventory=payload.sensor_inventory;hp.profile_review_state='REVIEW_REQUIRED'
    p.context_version+=1;audit(db,'hardware.draft',u.id,pid);db.commit()
    return {'id':hp.id,'profile_review_state':hp.profile_review_state,'board_model':hp.board_model}

@app.get('/api/projects/{pid}/context')
def context(pid:str,db:Session=Depends(get_db),u:User=Depends(current_user)):
    p,_=authorized(db,pid,u)
    hp=db.scalar(select(HardwareProfile).where(HardwareProfile.project_id==pid))
    return {'project_id':p.id,'owner_scope':p.owner_id,'name':p.name,'hardware_profile_id':hp.id if hp else None,'context_version':p.context_version,'source_revision_ids':[],'taskpack_id':None,'code_artifact_ids':[],'device_ids':[],'timestamp':now().isoformat()}

@app.get('/api/projects/{pid}/draft')
def get_draft(pid:str,db:Session=Depends(get_db),u:User=Depends(current_user)):
    authorized(db,pid,u)
    d=db.scalar(select(Conversation).where(Conversation.project_id==pid,Conversation.user_id==u.id))
    return {'draft':d.draft if d else ''}

@app.put('/api/projects/{pid}/draft',dependencies=[Depends(csrf_guard)])
def save_draft(pid:str,payload:DraftEdit,db:Session=Depends(get_db),u:User=Depends(current_user)):
    authorized(db,pid,u,write=True)
    d=db.scalar(select(Conversation).where(Conversation.project_id==pid,Conversation.user_id==u.id))
    if not d:d=Conversation(project_id=pid,user_id=u.id);db.add(d)
    d.draft=payload.draft;d.updated_at=now();db.commit();return {'draft':d.draft}

@app.get('/api/projects/{pid}/evidence')
def get_evidence(pid:str,db:Session=Depends(get_db),u:User=Depends(current_user)):
    authorized(db,pid,u)
    return {'events':[],'state':'NOT_IMPLEMENTED','message':'Physical evidence verification begins in Phase 04. No physical PASS exists.'}

@app.get('/api/projects/{pid}/twin')
def twin(pid:str,db:Session=Depends(get_db),u:User=Depends(current_user)):
    authorized(db,pid,u)
    return {'connection':'NOT_ENROLLED','telemetry':[],'origin':None,'message':'No real device enrolled or observed.'}

@app.get('/api/account/export')
def export_account(db:Session=Depends(get_db),u:User=Depends(current_user)):
    projs=[project_info(p,r) for p,r in db.execute(select(Project,Membership.role).join(Membership,Project.id==Membership.project_id).where(Membership.user_id==u.id)).all()]
    cons={c.kind:c.enabled for c in db.scalars(select(Consent).where(Consent.user_id==u.id))}
    return {'user':user_info(u),'projects':projs,'consents':cons}

@app.delete('/api/account',dependencies=[Depends(csrf_guard)])
def delete_account(response:Response,db:Session=Depends(get_db),u:User=Depends(current_user)):
    owned=db.scalars(select(Project).where(Project.owner_id==u.id)).all()
    for p in owned: db.delete(p)
    db.flush()
    db.delete(u);db.commit();clear(response)
    return {'deleted':True}
