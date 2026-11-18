import os, socket, threading, time
import pytest
import uvicorn
from playwright.sync_api import sync_playwright, expect
from app.main import create_app
from app.provision import provision
from conftest import SECRET,PASS

@pytest.fixture(scope='module')
def live(tmp_path_factory):
    path=tmp_path_factory.mktemp('live')/'browser.db';app=create_app('sqlite:///'+str(path),SECRET)
    provision(app.state.engine,'Demo','manager@nova.example',PASS,demo=True)
    sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    srv=uvicorn.Server(uvicorn.Config(app,log_level='warning',ws='none'));thread=threading.Thread(target=srv.run,kwargs={'sockets':[sock]},daemon=True);thread.start()
    for _ in range(100):
        if srv.started: break
        time.sleep(.05)
    assert srv.started
    yield f'http://127.0.0.1:{port}'
    srv.should_exit=True;thread.join(5);app.state.engine.dispose();sock.close()

@pytest.fixture
def browser():
    with sync_playwright() as p:
        binary=os.getenv('CHROMIUM_PATH')
        b=p.chromium.launch(headless=True,**({'executable_path':binary} if binary else {}));yield b;b.close()

def sign_in(page,live):
    page.goto(live);page.get_by_label('Correo electrónico').fill('manager@nova.example');page.get_by_label('Contraseña').fill(PASS);page.get_by_role('button',name='Iniciar sesión').click();expect(page.locator('#metrics')).to_contain_text('Prospectos')

def test_full_browser_flow(live,browser):
    page=browser.new_page(viewport={'width':1366,'height':900});errors=[];page.on('pageerror',lambda e: errors.append(str(e)));sign_in(page,live)
    if os.getenv('NOVA_SCREENSHOT'):page.screenshot(path=os.environ['NOVA_SCREENSHOT'],full_page=True)
    page.get_by_role('button',name='Prospectos').click();page.get_by_role('button',name='Nuevo prospecto').click();dialog=page.locator('#lead-dialog');dialog.get_by_label('Nombre').fill('Prueba Browser');dialog.get_by_label('Empresa').fill('Compañía QA');dialog.get_by_label('Ajuste al producto').fill('5');dialog.get_by_label('Presupuesto confirmado').check();dialog.get_by_label('Permiso de contacto registrado').check();dialog.get_by_role('button',name='Guardar prospecto').click()
    row=page.locator('tr').filter(has_text='Prueba Browser');expect(row).to_be_visible();row.get_by_role('button',name='Explicar').click();expect(page.locator('#detail')).to_contain_text('Índice experimental');page.locator('#close-detail').click();row.get_by_role('button',name='Sugerir').click();expect(page.locator('#message')).to_contain_text('Recomendación disponible');page.get_by_role('button',name='Revisiones').click();page.get_by_role('button',name='Aprobar').click();expect(page.locator('#review-list')).to_contain_text('approved');page.get_by_role('button',name='Tareas').click();page.get_by_role('button',name='Completar').click();expect(page.locator('#task-list')).to_contain_text('done');page.get_by_role('button',name='Asistente').click();page.get_by_label('Pregunta').fill('objeciones de precio descuento');page.get_by_role('button',name='Consultar guía').click();expect(page.locator('#answer')).to_contain_text('Objeciones de precio');page.get_by_role('button',name='Auditoría').click();expect(page.locator('#audit-list')).to_contain_text('review.approved');page.get_by_role('button',name='Cerrar sesión').click();expect(page.locator('#login')).to_be_visible();assert not errors,errors

def test_mobile_and_invalid_login(live,browser):
    page=browser.new_page(viewport={'width':390,'height':844},is_mobile=True,has_touch=True);page.goto(live);page.get_by_label('Correo electrónico').fill('manager@nova.example');page.get_by_label('Contraseña').fill('incorrect');page.get_by_role('button',name='Iniciar sesión').click();expect(page.locator('#login-error')).to_contain_text('Credenciales inválidas');sign_in(page,live);page.get_by_role('button',name='Prospectos').click();expect(page.locator('#lead-rows')).to_contain_text('Prospecto Alfa');assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth');page.close()
