"""Camada de interacao da janela: estado, mouse, menus, HUD e exibicao.

`view.py` continua render puro (geometria + desenho, sem syscalls); aqui
mora a maquina de estados da interface — menus de camera e de opcoes,
fila de botoes, wordmark, HUD — e os syscalls de janela (namedWindow,
setMouseCallback, imshow, waitKey), inclusive o helper de foreground do
WSLg. `run()` conversa com esta camada por `_camera_menu` e `_hud`,
os dois globals que o laço escreve.
"""

import os
import subprocess
import time

import cv2
import numpy as np

from . import camera as camera_module
from . import view as view_module
from .camera import LatestFrameCapture, _video_nodes, open_capture

# Janela curta de espera por quadro novo: longa demais e uma fonte
# em stall TCP (HelperCapture com stall_windows) congela as teclas
# de saida dentro de um unico read().
_FRAME_WAIT_SECONDS = 0.25


_WINDOW = "Draw"
_window_sized = set()
# Posicao de abertura. O WM escolhe sozinho e pode mapear a janela
# fora da area visivel: sob WSLg ela nasceu em x=2237 num desktop de
# 2944 px ("abre mas nao aparece"). O Qt so honra moveWindow com a
# janela ja realizada, entao o pedido se repete ate o prazo — em
# segundos, nao em exibicoes, para durar o mesmo em qualquer
# cadencia de quadros; depois o usuario posiciona livre. Em
# fullscreen o pedido nao sai — moveria a janela sem borda para
# fora da origem do monitor — mas o prazo corre igual: sair da
# tela cheia depois nao reabre o posicionamento.
_window_place_until = [0.0]
_WINDOW_PLACE_SECONDS = 2.5
_WINDOW_PLACE_X, _WINDOW_PLACE_Y = 96, 48
# Titulo unico por lancamento no WSLg: "Draw <pid>-<hex>" identifica a
# hwnd desta sessao para o helper de foreground, sem confundir sessoes
# abertas — o pid sozinho colide entre distros (namespaces separados).
# Volta a "Draw" quando o helper renomeia a janela ou, na falta dele,
# ao expirar o prazo local (busca do helper + margem).
_window_token = [None]
_window_title_restore_at = [0.0]
_WSL_RAISE_POLLS = 240  # ~60 s: o RAIL pode demorar a publicar a hwnd
_WSL_RAISE_POLL_MS = 250
# O prazo local cobre a vida inteira do helper com folga: cada sonda
# paga o EnumWindows alem do sleep, entao a duracao real passa do
# nominal — restaurar o titulo no meio da busca perderia o raise.
_WSL_TITLE_RESTORE_SECONDS = _WSL_RAISE_POLLS * _WSL_RAISE_POLL_MS / 1000 * 1.5 + 10.0


_mouse = {}


_UI_TICK_SECONDS = 0.016
_HOVER_SECONDS = 0.22
_WORDMARK_SECONDS = 0.6
_wordmark_state = {"progress": 0.0, "origin": None, "time": None, "inside": False}
_button_state = {"progress": [], "pressed": None, "queue": [], "time": None}


def _button_at(x, y):
    for i, (bx, by, bw, bh) in enumerate(view_module.button_rects(_window_size())):
        if bx <= x < bx + bw and by - 3 <= y < by + bh:
            return i
    return None


_CAMERA_MENU_SECONDS = 0.18
_SWITCH_READY_SECONDS = 10.0
_TOGGLE_SECONDS = 0.35
_REACT_SECONDS = 0.9
_camera_menu = {
    "open": False,
    "progress": 0.0,
    "dot": 0.0,
    "rows": [],
    "items": [],
    "current": None,
    "busy": None,
    "notice": None,
    "notice_until": 0.0,
    "request": None,
    "time": None,
    "scroll": 0,
    "cam_shape": (512, 512, 3),
}


def _camera_label(source):
    if isinstance(source, int):
        return f"Camera {source}"
    text = str(source)
    if "://" in text:
        return "Rede: " + text.split("://", 1)[1].split("/")[0][:20]
    return os.path.basename(text)[:22] or text[:22]


def _list_cameras(current):
    """Cameras para o menu: os /dev/video* e a fonte atual, se for outra."""
    items = [
        (_camera_label(index), index)
        for index in (int(node[len("/dev/video") :]) for node in _video_nodes())
    ]
    if current not in [source for _, source in items]:
        items.insert(0, (_camera_label(current), current))
    return items


def _camera_layout():
    count = len(_camera_menu["items"])
    return view_module.camera_menu_layout(
        _window_size(),
        _camera_menu["cam_shape"],
        view_module.blank_sheet().shape,
        count,
        _camera_menu["scroll"],
    )


def _camera_click(x, y):
    """Clique na bolinha ou no menu de cameras. True se o clique foi usado."""
    state = _camera_menu
    layout = _camera_layout()
    if state["open"]:
        step = view_module.scroll_hit(layout, (x, y))
        if step is not None:
            top = layout["count"] - layout["visible"]
            state["scroll"] = max(0, min(top, layout["first"] + step))
            return True
        row = view_module.row_at(layout, (x, y))
        on_dot = view_module.point_in_dot(layout, (x, y))
        state["open"] = False
        row = None if row is None else layout["first"] + row
        if row is not None and row < len(state["items"]):
            source = state["items"][row][1]
            if source != state["current"] and state["busy"] is None:
                state["request"] = source
            return True
        return on_dot
    if view_module.point_in_dot(layout, (x, y)):
        state["items"] = _list_cameras(state["current"])
        state["scroll"] = 0
        state["open"] = True
        _settings["open"] = False
        return True
    return False


def _camera_fx():
    """Estado animado da bolinha e do menu de cameras para o desenho."""
    state = _camera_menu
    now = time.monotonic()
    last, state["time"] = state["time"], now
    dt = 0.0 if last is None else now - last
    pos = _mouse.get("pos")
    layout = _camera_layout()
    step = dt / _CAMERA_MENU_SECONDS
    on_dot = pos is not None and view_module.point_in_dot(layout, pos)
    state["dot"] += max(-step, min(step, (1.0 if on_dot else 0.0) - state["dot"]))
    target = 1.0 if state["open"] else 0.0
    state["progress"] += max(-step, min(step, target - state["progress"]))
    count = len(state["items"])
    if len(state["rows"]) != count:
        state["rows"] = [0.0] * count
    hovered = (
        view_module.row_at(layout, pos) if pos is not None and state["open"] else None
    )
    if hovered is not None:
        hovered += layout["first"]
    for i in range(count):
        goal = 1.0 if hovered == i else 0.0
        state["rows"][i] += max(-step, min(step, goal - state["rows"][i]))
    items = []
    for (label, source), hover in zip(state["items"], state["rows"], strict=True):
        if source == state["busy"]:
            label = "Abrindo..."
        elif source == state["notice"] and now < state["notice_until"]:
            label = "Nao abriu"
        items.append(
            {"label": label, "selected": source == state["current"], "hover": hover}
        )
    first = layout["first"]
    return {
        "dot": state["dot"],
        "opened": state["open"],
        "progress": state["progress"],
        "items": items[first : first + layout["visible"]],
        "count": count,
        "first": first,
    }


_SETTINGS_ITEMS = (
    ("probe", "Coordenadas e RGB"),
    ("latency", "Latencia"),
    ("fps", "FPS"),
    ("fullscreen", "Tela cheia"),
)
_settings = {
    "open": False,
    "progress": 0.0,
    "gear": 0.0,
    "rows": [0.0] * len(_SETTINGS_ITEMS),
    "on_p": [0.0] * len(_SETTINGS_ITEMS),
    "react": [1.0] * len(_SETTINGS_ITEMS),
    "dir": [1] * len(_SETTINGS_ITEMS),
    "time": None,
    "on": {key: False for key, _ in _SETTINGS_ITEMS},
}
_hud = {"captured_at": None, "fps": None}
_fullscreen_applied = [False]


def _settings_layout():
    return view_module.settings_menu_layout(_window_size(), len(_SETTINGS_ITEMS))


def _settings_click(x, y):
    """Clique na engrenagem ou no menu de opcoes. True se foi usado."""
    state = _settings
    layout = _settings_layout()
    on_gear = view_module.point_in_gear(layout, (x, y))
    if state["open"]:
        row = view_module.row_at(layout, (x, y))
        if row is not None and row < len(_SETTINGS_ITEMS):
            key = _SETTINGS_ITEMS[row][0]
            state["on"][key] = not state["on"][key]
            state["dir"][row] = 1 if state["on"][key] else -1
            state["react"][row] = 0.0
            return True
        state["open"] = False
        return on_gear
    if on_gear:
        state["open"] = True
        _camera_menu["open"] = False
        return True
    return False


def _settings_fx():
    """Estado animado da engrenagem e do menu de opcoes para o desenho."""
    state = _settings
    now = time.monotonic()
    last, state["time"] = state["time"], now
    step = 0.0 if last is None else (now - last) / _CAMERA_MENU_SECONDS
    pos = _mouse.get("pos")
    layout = _settings_layout()
    on_gear = pos is not None and view_module.point_in_gear(layout, pos)
    state["gear"] += max(-step, min(step, (1.0 if on_gear else 0.0) - state["gear"]))
    target = 1.0 if state["open"] else 0.0
    state["progress"] += max(-step, min(step, target - state["progress"]))
    hovered = (
        view_module.row_at(layout, pos) if pos is not None and state["open"] else None
    )
    items = []
    for i, (key, label) in enumerate(_SETTINGS_ITEMS):
        goal = 1.0 if hovered == i else 0.0
        state["rows"][i] += max(-step, min(step, goal - state["rows"][i]))
        dt = 0.0 if last is None else now - last
        slide = dt / _TOGGLE_SECONDS
        aim = 1.0 if state["on"][key] else 0.0
        state["on_p"][i] += max(-slide, min(slide, aim - state["on_p"][i]))
        state["react"][i] = min(1.0, state["react"][i] + dt / _REACT_SECONDS)
        items.append(
            {
                "label": label,
                "on": state["on"][key],
                "hover": state["rows"][i],
                "on_p": state["on_p"][i],
                "dir": state["dir"][i],
                "react": state["react"][i],
            }
        )
    return {
        "gear": state["gear"],
        "opened": state["open"],
        "progress": state["progress"],
        "items": items,
    }


def _hud_values():
    """Valores do painel da camera: so o que esta ligado na engrenagem."""
    on = _settings["on"]
    captured_at = _hud["captured_at"]
    latency = None
    if on["latency"] and captured_at is not None:
        latency = (time.monotonic() - captured_at) * 1000.0
    return {
        "probe": _mouse.get("pos") if on["probe"] else None,
        "latency": latency,
        "fps": _hud["fps"] if on["fps"] else None,
    }


_view_map = {"scale": 1.0, "offset": (0, 0)}


def _on_mouse(event, x, y, flags, param):
    scale, (ox, oy) = _view_map["scale"], _view_map["offset"]
    x, y = int((x - ox) / scale), int((y - oy) / scale)
    _mouse["pos"] = (x, y)
    if event == cv2.EVENT_LBUTTONUP and (_settings_click(x, y) or _camera_click(x, y)):
        _button_state["pressed"] = None
        return
    if event == cv2.EVENT_LBUTTONDOWN:
        _button_state["pressed"] = _button_at(x, y)
    elif event == cv2.EVENT_LBUTTONUP:
        pressed, _button_state["pressed"] = _button_state["pressed"], None
        if pressed is not None and pressed == _button_at(x, y):
            keys = view_module.footer_buttons()
            _button_state["queue"].append(ord(keys[pressed][2]))


def _button_fx():
    """Progresso de hover (0..1) por botao, suavizado no tempo."""
    count = len(view_module.footer_buttons())
    progress = _button_state["progress"]
    if len(progress) != count:
        progress[:] = [0.0] * count
    now = time.monotonic()
    last = _button_state["time"]
    _button_state["time"] = now
    step = 0.0 if last is None else (now - last) / _HOVER_SECONDS
    pos = _mouse.get("pos")
    hovered = _button_at(*pos) if pos is not None else None
    for i in range(count):
        target = 1.0 if hovered == i else 0.0
        progress[i] += max(-step, min(step, target - progress[i]))
    return list(progress)


def _ui_state():
    """Estado visual da interface fora da camera: pisca, botoes, mouse, janela."""
    return {
        "rec_on": _rec_on(),
        "buttons": _button_fx(),
        "pressed": _button_state["pressed"],
        "size": _window_size(),
        "pos": _mouse.get("pos"),
        "wordmark": _wordmark_fx(),
        "camera": _camera_fx(),
        "settings": _settings_fx(),
        "hud": _hud_values(),
    }


def _ui_signature(ui):
    return (
        ui["rec_on"],
        tuple(round(v, 3) for v in ui["buttons"]),
        ui["pressed"],
        ui["size"],
        ui["pos"],
        round(ui["wordmark"][0], 3),
        round(ui["camera"]["dot"], 3),
        round(ui["camera"]["progress"], 3),
        tuple(round(item["hover"], 3) for item in ui["camera"]["items"]),
        tuple(item["label"] for item in ui["camera"]["items"]),
        round(ui["settings"]["gear"], 3),
        round(ui["settings"]["progress"], 3),
        tuple(
            (round(item["hover"], 3), round(item["on_p"], 3), round(item["react"], 3))
            for item in ui["settings"]["items"]
        ),
        None if ui["hud"]["latency"] is None else int(ui["hud"]["latency"] // 25),
        None if ui["hud"]["fps"] is None else round(ui["hud"]["fps"], 1),
    )


def _wordmark_fx():
    """Progresso do hover no nome DRAW e ponto onde o mouse o tocou."""
    state = _wordmark_state
    now = time.monotonic()
    last, state["time"] = state["time"], now
    step = 0.0 if last is None else (now - last) / _WORDMARK_SECONDS
    pos = _mouse.get("pos")
    inside = False
    if pos is not None:
        bx, by, bw, bh = view_module.wordmark_rect(_window_size())
        inside = bx <= pos[0] < bx + bw and by <= pos[1] < by + bh
    if inside and not state["inside"]:
        state["origin"] = pos
    state["inside"] = inside
    target = 1.0 if inside else 0.0
    state["progress"] += max(-step, min(step, target - state["progress"]))
    return state["progress"], state["origin"]


def _next_key():
    """Tecla do waitKey ou, se nao houver, um clique de botao pendente."""
    key = cv2.waitKey(1) & 0xFF
    queue = _button_state["queue"]
    if key == 0xFF and queue:
        return queue.pop(0)
    return key


def _rec_on():
    """Alterna o ponto de gravacao a cada 1 s."""
    return int(time.monotonic() / 1.0) % 2 == 0


def _window_rect():
    """Largura e altura da area de desenho da janela, ou None sem janela."""
    try:
        _, _, w, h = cv2.getWindowImageRect(_WINDOW)
    except cv2.error:
        return None
    return w, h


def _window_size():
    """Tamanho atual da area de desenho da janela (padrao antes de abrir)."""
    default = (1600, 640)
    rect = _window_rect() if _window_sized else None
    return rect if rect and rect[0] >= 320 and rect[1] >= 160 else default


def _start_wsl_foreground_helper(token):
    """Lanca o helper que traz a janela nova para frente do desktop Windows.

    O WSLg mapeia a janela abaixo da janela ativa do Windows — com um
    browser maximizado ela nasce invisivel mesmo dentro da tela. O
    Wayland nao deixa o cliente se levantar (move/raise/_NET_ACTIVE_WINDOW
    e o TOPMOST do Qt sao engolidos), entao a subida vai pelo lado
    Windows: AttachThreadInput na thread da janela ativa +
    SetForegroundWindow. A hwnd e identificada pelo titulo unico do
    lancamento — o RAIL pode adicionar afixos em volta (" (Ubuntu)",
    "[WARN:COPY MODE] ..." com captura de tela ativa), entao a busca e
    por substring e sessoes antigas nunca entram nela. Ao achar, o
    helper levanta a janela e
    devolve o titulo normal via SetWindowText. Retorna o processo ou
    None fora do WSL/se o powershell nao subir; falhar em qualquer
    passo so perde a subida, nada mais.
    """
    if not camera_module.is_wsl():
        return None
    ps = (
        "$s='using System;using System.Text;using System.Runtime.InteropServices;"
        'public class W{[DllImport("user32.dll")]public static extern bool '
        "EnumWindows(E e,IntPtr l);public delegate bool E(IntPtr h,IntPtr l);"
        '[DllImport("user32.dll")]public static extern int GetWindowTextA('
        'IntPtr h,StringBuilder s,int n);[DllImport("user32.dll")]public static '
        "extern bool SetWindowTextA(IntPtr h,string s);"
        '[DllImport("user32.dll")]public static '
        'extern IntPtr GetForegroundWindow();[DllImport("user32.dll")]public '
        "static extern uint GetWindowThreadProcessId(IntPtr h,out uint p);"
        '[DllImport("user32.dll")]public static extern bool AttachThreadInput('
        'uint a,uint b,bool at);[DllImport("user32.dll")]public static extern '
        'bool SetForegroundWindow(IntPtr h);[DllImport("user32.dll")]public '
        "static extern bool BringWindowToTop(IntPtr h);"
        '[DllImport("user32.dll")]public static extern bool ShowWindowAsync('
        'IntPtr h,int n);[DllImport("kernel32.dll")]public static extern uint '
        "GetCurrentThreadId();}';"
        "Add-Type -TypeDefinition $s;$t=[IntPtr]::Zero;$n=0;"
        "while($t -eq [IntPtr]::Zero -and $n -lt __POLLS__){$n++;"
        "[W]::EnumWindows({param($h,$l)$b=New-Object Text.StringBuilder 512;"
        "[W]::GetWindowTextA($h,$b,512)|Out-Null;"
        "if($b.ToString() -like '*__TOKEN__*'){$script:t=$h};return $true},"
        "[IntPtr]::Zero)|Out-Null;"
        "if($t -eq [IntPtr]::Zero){Start-Sleep -Milliseconds __POLLMS__}};"
        "if($t -ne [IntPtr]::Zero){$fg=[W]::GetForegroundWindow();"
        "$ft=[W]::GetWindowThreadProcessId($fg,[ref]([uint32]$p=0));"
        "$me=[W]::GetCurrentThreadId();"
        "[W]::AttachThreadInput($me,$ft,$true)|Out-Null;"
        "[W]::ShowWindowAsync($t,5)|Out-Null;"
        "[W]::BringWindowToTop($t)|Out-Null;"
        "[W]::SetForegroundWindow($t)|Out-Null;"
        "[W]::AttachThreadInput($me,$ft,$false)|Out-Null;"
        "[W]::SetWindowTextA($t,'__TITLE__')|Out-Null}"
    )
    ps = (
        ps.replace("__TOKEN__", token)
        .replace("__POLLS__", str(_WSL_RAISE_POLLS))
        .replace("__POLLMS__", str(_WSL_RAISE_POLL_MS))
        .replace("__TITLE__", _WINDOW)
    )
    try:
        return subprocess.Popen(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError:
        return None


def _publish_unique_title_and_raise():
    """Publica o titulo unico do lancamento e dispara o helper de foreground.

    A janela sai como "Draw <pid>-<hex>" — o RAIL a apresenta no Windows
    como "Draw <pid>-<hex> (Ubuntu)", com possiveis afixos extras — e
    o helper casa por substring, entao nenhuma sessao antiga pode ser
    levantada por engano. O
    titulo volta a "Draw" quando o helper renomeia a hwnd ou, sem ele,
    ao expirar o prazo local. Sem GUI do Qt o passo e ignorado.
    """
    if not camera_module.is_wsl():
        return
    token = f"{_WINDOW} {os.getpid()}-{os.urandom(3).hex()}"
    try:
        cv2.setWindowTitle(_WINDOW, token)
    except cv2.error:
        return
    _window_token[0] = token
    _window_title_restore_at[0] = time.monotonic() + _WSL_TITLE_RESTORE_SECONDS
    _start_wsl_foreground_helper(token)


def _open_window(fullscreen):
    """Cria a janela do Draw: sem barras do Qt, redimensionavel, com mouse."""
    cv2.namedWindow(
        _WINDOW,
        cv2.WINDOW_NORMAL | cv2.WINDOW_GUI_NORMAL | cv2.WINDOW_FREERATIO,
    )
    _window_sized.clear()
    _window_place_until[0] = 0.0
    _settings["on"]["fullscreen"] = fullscreen
    _fullscreen_applied[0] = False
    cv2.setMouseCallback(_WINDOW, _on_mouse)
    _publish_unique_title_and_raise()


def _ui_wait_seconds():
    """Espera por quadro: curta com o mouse na janela, para a interface fluir."""
    return _UI_TICK_SECONDS if _mouse.get("pos") is not None else _FRAME_WAIT_SECONDS


def _apply_fullscreen():
    """Liga ou desliga a tela cheia, que esconde a moldura da janela."""
    want = _settings["on"]["fullscreen"]
    if _fullscreen_applied[0] != want:
        _fullscreen_applied[0] = want
        cv2.setWindowProperty(
            _WINDOW,
            cv2.WND_PROP_FULLSCREEN,
            cv2.WINDOW_FULLSCREEN if want else cv2.WINDOW_NORMAL,
        )


def _open_ready_source(target, helper_token_file=None, ready_seconds=None, rotation=0):
    """Abre a fonte e so a devolve depois do primeiro quadro; senao levanta.

    A fonte antiga so e trocada por uma que ja entregou quadro: uma
    camera que abre mas nao le deixa a atual no ar. O orcamento de
    ready_seconds conta desde o inicio da abertura (a recuperacao de
    exposicao do open_capture pode gastar varios segundos); a espera
    pelo primeiro quadro usa o que sobrou, com piso de 1 s. A abertura
    em si nao e cancelavel, mas roda numa thread e nao trava a janela.
    """
    started = time.monotonic()
    capture = open_capture(target, helper_token_file=helper_token_file)
    candidate = LatestFrameCapture(capture, rotation=rotation).start()
    budget = _SWITCH_READY_SECONDS if ready_seconds is None else ready_seconds
    remaining = max(1.0, budget - (time.monotonic() - started))
    if candidate.wait_next(0, timeout=remaining) is None:
        candidate.stop(force=False)
        raise RuntimeError("a camera abriu mas nao entregou quadros")
    return candidate


def _waiting_view():
    """Quadro de camera vazio com o aviso, para a interface seguir completa."""
    image = np.zeros((720, 1280, 3), dtype=np.uint8)
    for i, text in enumerate(
        ("Aguardando quadros da fonte", "A leitura esta lenta ou parada.")
    ):
        cv2.putText(
            image,
            text,
            (320, 330 + i * 48),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0 if i == 0 else 0.7,
            (230, 235, 235) if i == 0 else (150, 156, 154),
            2 if i == 0 else 1,
            cv2.LINE_AA,
        )
    return image


def _show(image):
    """Mostra o quadro na janela sem deixar o Qt reescalar a imagem.

    A vista tem tamanho fixo; maximizada, o Qt a esticaria com filtro
    barato. Aqui o redimensionamento e feito com interpolacao de
    qualidade, mantendo a proporcao e preenchendo o resto com o fundo.
    Na primeira exibicao a janela abre no tamanho nativo da vista.
    """
    _apply_fullscreen()
    ih, iw = image.shape[:2]
    if not _window_sized:
        cv2.resizeWindow(_WINDOW, iw, ih)
        _window_sized.add(True)
        _window_place_until[0] = time.monotonic() + _WINDOW_PLACE_SECONDS
    elif (
        not _settings["on"]["fullscreen"] and time.monotonic() < _window_place_until[0]
    ):
        try:
            cv2.moveWindow(_WINDOW, _WINDOW_PLACE_X, _WINDOW_PLACE_Y)
        except cv2.error:
            _window_place_until[0] = 0.0
    if _window_token[0] is not None and time.monotonic() >= _window_title_restore_at[0]:
        try:
            cv2.setWindowTitle(_WINDOW, _WINDOW)
        except cv2.error:
            pass
        _window_token[0] = None
    w, h = _window_rect() or (0, 0)
    _view_map.update(scale=1.0, offset=(0, 0))
    if w > 0 and h > 0 and (w, h) != (iw, ih):
        scale = min(w / iw, h / ih)
        nw, nh = max(1, round(iw * scale)), max(1, round(ih * scale))
        interp = cv2.INTER_AREA if scale < 1 else cv2.INTER_LANCZOS4
        image = cv2.resize(image, (nw, nh), interpolation=interp)
        dx, dy = max(0, w - nw), max(0, h - nh)
        _view_map.update(scale=nw / iw, offset=(dx // 2, dy // 2))
        image = cv2.copyMakeBorder(
            image,
            dy // 2,
            dy - dy // 2,
            dx // 2,
            dx - dx // 2,
            cv2.BORDER_CONSTANT,
            value=view_module.COLOR_BG_STUDIO,
        )
    cv2.imshow(_WINDOW, image)
