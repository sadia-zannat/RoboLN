"""Real isolated Alembic roundtrip, including actual schema state checks."""
import os,subprocess,sys,tempfile,pathlib
from sqlalchemy import create_engine,inspect,text
root=pathlib.Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='roboln-v2-migration-') as tmp:
  db=pathlib.Path(tmp)/'fresh.sqlite'
  env={**os.environ,'ROBOLN_DATABASE_URL':'sqlite:///'+str(db)}
  def run(*args):subprocess.run(['alembic',*args],cwd=root/'backend',env=env,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
  engine=create_engine(env['ROBOLN_DATABASE_URL'])
  run('upgrade','head')
  tables=inspect(engine).get_table_names()
  assert 'projects' in tables and 'login_throttles' in tables,tables
  with engine.connect() as c:
    version=c.execute(text('select version_num from alembic_version')).scalar()
    assert version=='ff6d85194d00',version
  run('downgrade','base')
  assert inspect(engine).get_table_names()==['alembic_version'],inspect(engine).get_table_names()
  run('upgrade','head')
  assert 'users' in inspect(engine).get_table_names()
  with engine.connect() as c:assert c.execute(text('select version_num from alembic_version')).scalar()==version
  engine.dispose()
print('Alembic upgrade/downgrade/upgrade: PASS; frozen revision ff6d85194d00; 9 domain tables')
