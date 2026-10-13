"""Executa testes MySQL reais com relatorio sem credenciais nem tracebacks."""
from pathlib import Path
import os,sys,json,contextlib,fcntl
from datetime import datetime,timezone
import pytest
BASE=Path(__file__).resolve().parent
BACKEND=BASE.parent
STATE=BACKEND/'.local/mysql'
class Report:
    def __init__(self,password=''): self.items=[]; self.password=password
    def pytest_configure(self,config): config.mysql_admin_password=self.password
    def pytest_runtest_logreport(self,report):
        if report.when=='call' or report.failed:
            self.items.append({'teste':report.nodeid,'fase':report.when,'resultado':{'passed':'aprovado','failed':'falhou','skipped':'nao_executado'}[report.outcome]})
    def pytest_collectreport(self,report):
        if report.failed: self.items.append({'teste':'coleta','fase':'coleta','resultado':'falhou'})
def main():
    os.umask(0o077)
    STATE.mkdir(parents=True,exist_ok=True,mode=0o700)
    from getpass import getpass
    password=getpass('Senha administrativa existente (oculta): ') if '--admin-password' in sys.argv else ''
    test_lock=(STATE/'testes.lock').open('a')
    fcntl.flock(test_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    os.environ['RUN_MYSQL_TESTS']='1'
    os.chdir(BACKEND);sys.path.insert(0,str(BACKEND))
    report=Report(password)
    with open(os.devnull,'w') as null,contextlib.redirect_stdout(null),contextlib.redirect_stderr(null):
        result=pytest.main(['tests/test_mysql_auth_real.py','-q','--tb=no','-p','no:cacheprovider'],plugins=[report])
    complete=result==0 and len([i for i in report.items if i['fase']=='call' and i['resultado']=='aprovado'])==6 and all(i['resultado']=='aprovado' for i in report.items)
    output={'executado_em_utc':datetime.now(timezone.utc).isoformat(),'exit_code':int(result),'testes':report.items,'status':'aprovado' if complete else ('falhou' if result else 'nao_executado'),'observacao':'Nenhuma credencial, hash, cookie ou token registrado. Falhas exigem revisao local; nao declarar banco pronto.'}
    (STATE/'relatorio_testes_reais.json').write_text(json.dumps(output,indent=2,ensure_ascii=False)+'\n')
    print('Testes reais:',output['status'])
    return 0 if complete else int(result) or 1
if __name__=='__main__': raise SystemExit(main())
