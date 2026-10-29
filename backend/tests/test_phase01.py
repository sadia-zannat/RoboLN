import pytest
from jsonschema import validate
from pathlib import Path
import json
from .conftest import csrf


def create(c,name='Rover alpha'):
    return c.post('/api/projects',json={'name':name,'description':'Real project'},headers=csrf(c))

def test_signup_login_csrf_logout(client,register):
    assert client.get('/api/auth/me').status_code==401
    u=register(client)
    assert client.get('/api/auth/me').json()['id']==u['id']
    assert client.post('/api/projects',json={'name':'Should fail'}).status_code==403
    assert client.post('/api/projects',json={'name':'Nope'},headers={'x-csrf-token':'wrong'}).status_code==403
    assert client.post('/api/projects',json={'name':'Nope'},headers={**csrf(client),'origin':'https://evil.example'}).status_code==403
    assert create(client).status_code==201
    assert client.post('/api/auth/logout',headers=csrf(client)).status_code==200
    assert client.get('/api/auth/me').status_code==401
    assert client.post('/api/auth/login',json={'email':u['email'],'password':'wrong-password-long'}).status_code==401
    assert client.post('/api/auth/login',json={'email':u['email'],'password':'SafePasswordExample123!'}).status_code==200
    assert len(client.get('/api/projects').json())==1


def test_projects_crud_and_hardware_context(client,register):
    register(client)
    a=create(client)
    assert a.status_code==201,a.text
    pid=a.json()['id']
    assert client.get('/api/projects/'+pid).json()['name']=='Rover alpha'
    assert client.patch('/api/projects/'+pid,json={'name':'Smart Rover','description':'New','goal':'measure only'},headers=csrf(client)).status_code==200
    hw=client.put(f'/api/projects/{pid}/hardware',json={'device_class':'MCU','board_model':'ESP32-S3 user-provided','board_revision':'unverified','pin_map':{}},headers=csrf(client))
    assert hw.status_code==200,hw.text
    assert hw.json()['profile_review_state']=='REVIEW_REQUIRED'
    ctx=client.get(f'/api/projects/{pid}/context').json()
    schema=json.loads((Path(__file__).parents[2]/'packages/contracts/project_context.schema.json').read_text())
    validate(ctx,schema)
    assert ctx['context_version']==3
    assert ctx['hardware_profile_id']
    assert client.put(f'/api/projects/{pid}/draft',json={'draft':'Ask about sensor pins'},headers=csrf(client)).status_code==200
    assert client.get(f'/api/projects/{pid}/draft').json()['draft']=='Ask about sensor pins'
    assert client.post(f'/api/projects/{pid}/archive',headers=csrf(client)).json()['archived']
    assert client.delete(f'/api/projects/{pid}',headers=csrf(client)).status_code==204
    assert client.get(f'/api/projects/{pid}').status_code==404


def test_isolation_viewer_editor_owner(client,register):
    owner=register(client)
    a=create(client).json()['id']
    b=create(client,'Second private rover').json()['id']
    client.post('/api/auth/logout',headers=csrf(client))
    viewer=register(client,'viewer@example.com','Viewer')
    assert client.get(f'/api/projects/{a}').status_code==404
    assert client.get(f'/api/projects/{a}/hardware').status_code==404
    assert client.get(f'/api/projects/{b}/draft').status_code==404
    client.post('/api/auth/logout',headers=csrf(client))
    client.post('/api/auth/login',json={'email':owner['email'],'password':'SafePasswordExample123!'})
    assert client.put(f'/api/projects/{a}/members',json={'email':viewer['email'],'role':'viewer'},headers=csrf(client)).status_code==200
    client.post('/api/auth/logout',headers=csrf(client))
    client.post('/api/auth/login',json={'email':viewer['email'],'password':'SafePasswordExample123!'})
    assert client.get(f'/api/projects/{a}').status_code==200
    assert client.get(f'/api/projects/{b}').status_code==404
    assert client.patch(f'/api/projects/{a}',json={'name':'Malicious'},headers=csrf(client)).status_code==403
    assert client.delete(f'/api/projects/{a}',headers=csrf(client)).status_code==403
    assert client.put(f'/api/projects/{a}/hardware',json={'board_model':'bad'},headers=csrf(client)).status_code==403
    assert client.put(f'/api/projects/{a}/draft',json={'draft':'should fail'},headers=csrf(client)).status_code==403
    assert client.get(f'/api/projects/{a}/evidence').json()['events']==[]
    client.post('/api/auth/logout',headers=csrf(client))
    client.post('/api/auth/login',json={'email':owner['email'],'password':'SafePasswordExample123!'})
    assert client.put(f'/api/projects/{a}/members',json={'email':viewer['email'],'role':'editor'},headers=csrf(client)).status_code==200
    client.post('/api/auth/logout',headers=csrf(client))
    client.post('/api/auth/login',json={'email':viewer['email'],'password':'SafePasswordExample123!'})
    assert client.patch(f'/api/projects/{a}',json={'name':'Editor update'},headers=csrf(client)).status_code==200
    assert client.post(f'/api/projects/{a}/archive',headers=csrf(client)).status_code==403


def test_preferences_consents_export_delete(client,register):
    register(client)
    assert client.patch('/api/preferences/theme',json={'theme':'dark'},headers=csrf(client)).json()['theme']=='dark'
    assert client.put('/api/consents/camera',json={'enabled':True},headers=csrf(client)).json()['enabled']
    assert client.get('/api/consents').json()['camera']
    assert client.patch('/api/profile',json={'full_name':'New Name'},headers=csrf(client)).json()['full_name']=='New Name'
    p=create(client).json()['id']
    exported=client.get('/api/account/export').json()
    assert exported['projects'][0]['id']==p
    assert exported['consents']['camera'] is True
    assert client.delete('/api/account',headers=csrf(client)).json()['deleted']
    assert client.get('/api/auth/me').status_code==401
    assert client.post('/api/auth/login',json={'email':'owner@example.com','password':'SafePasswordExample123!'}).status_code==401


def test_negative_inputs_and_trust_boundary(client,register):
    register(client)
    assert create(client,'a').status_code==422
    assert client.get('/api/projects/00000000-0000-0000-0000-000000000000').status_code==404
    assert client.put('/api/consents/nonexistent',json={'enabled':True},headers=csrf(client)).status_code==422
    assert client.put('/api/projects/anything/hardware',json={'device_class':'ROCKET'},headers=csrf(client)).status_code==422
    assert client.get('/api/health').json()['telemetry']=='NOT_IMPLEMENTED'


def test_login_throttle_is_db_persistent(client,register):
    register(client)
    client.post('/api/auth/logout',headers=csrf(client))
    for _ in range(5):
        assert client.post('/api/auth/login',json={'email':'owner@example.com','password':'WrongPassword123!'}).status_code==401
    assert client.post('/api/auth/login',json={'email':'owner@example.com','password':'SafePasswordExample123!'}).status_code==429


def test_whitespace_names_and_bounded_hardware_are_rejected(client, register):
    register(client)
    pid=create(client).json()['id']
    assert client.patch(f'/api/projects/{pid}', json={'name':'     '},headers=csrf(client)).status_code==422
    assert client.patch('/api/profile',json={'full_name':'   '},headers=csrf(client)).status_code==422
    oversize={f'pin{i}':'value' for i in range(101)}
    assert client.put(f'/api/projects/{pid}/hardware',json={'pin_map':oversize},headers=csrf(client)).status_code==422
    assert client.get(f'/api/projects/{pid}').json()['name']=='Rover alpha'

def test_archived_project_is_read_only_until_restored(client, register):
    register(client)
    pid=create(client).json()['id']
    assert client.post(f'/api/projects/{pid}/archive',headers=csrf(client)).status_code==200
    assert client.patch(f'/api/projects/{pid}',json={'name':'Should not save'},headers=csrf(client)).status_code==409
    assert client.put(f'/api/projects/{pid}/hardware',json={'board_model':'Should not save'},headers=csrf(client)).status_code==409
    assert client.post(f'/api/projects/{pid}/archive',headers=csrf(client)).status_code==200
    assert client.patch(f'/api/projects/{pid}',json={'name':'Restored'},headers=csrf(client)).status_code==200
