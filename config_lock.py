# -*- coding: utf-8 -*-
"""
config_lock.py — Utilitário de TRAVA única de escrita (single-writer lock)
para arquivos de configuração, focado no ambiente Windows (msvcrt nativo).

O objetivo deste módulo é proteger o acesso concorrente a `config.json`
(ou a qualquer outro arquivo de config). Múltiplas sessões/processos podem
tentar editar o config em paralelo; esta trava garante que apenas um
"escritor" obtenha o direito exclusivo de modificá-lo por vez.

REGRAS OPERACIONAIS IMPLEMENTADAS
---------------------------------
1. NÃO toca no arquivo de config protegido (ex.: `config.json`). Ele jamais
   é aberto, lido ou escrito por este módulo — apenas o lock file derivado
   (`<path>.lock`) é manipulado.
2. O lock file é SEMPRE `<path>.lock` (ex.: `config.json.lock`).
3. A aquisição é feita via `msvcrt.locking` sobre 1 byte (LK_NBLCK, não
   bloqueante), com retry em loop (intervalo ~0.1s) até `timeout` segundos.
   Usamos LK_NBLCK no lugar de LK_LOCK justamente para poder honrar o
   `timeout` com retry controlado.
4. Detecção de trava órfã (stale lock): se o lock file existir mas sua
   `st_mtime` for mais antiga que STALE_SECONDS (5 minutos), o lock é
   considerado órfão e é quebrado automaticamente (arquivo borrado/zerado)
   antes de tentar adquirir. Isso evita trava eterna após crash do titular.
5. `force=True`: borra/remove o lock file antes de adquirir (quebra imediata,
   além da stale detection).
6. Reentrância: NÃO é reentrante. Uma segunda aquisição do mesmo lock
   (mesmo processo segurando OU outro processo) enquanto a primeira está
   ativa levanta `LockTimeoutError`. No Windows, o próprio msvcrt recusa a
   re-lockagem de região já travada mesmo no mesmo processo (via segundo
   handle), e nós não implementamos reentrância artificial — a trava
   representa uma única operação de escrita por vez.

FORMATO DO LOCK FILE
--------------------
O arquivo `<path>.lock` tem tamanho fixo (LOCK_FILE_SIZE = 256 bytes):
    [0:1]   byte de trava — região travada via msvcrt.locking (1 byte)
    [1:255] metadados textuais ("v1|pid=<PID>|ts=<EPOCH>\n" + padding)

Guardar os metadados a partir do offset 1 (não no byte travado) permite que
`lock_info` leia o PID/timestamp mesmo quando outro processo está segurando
a trava (o byte 0 fica bloqueado, mas os bytes seguintes continuam legíveis).

PUBLIC API
----------
- lock_config(path="config.json", timeout=10.0, force=False) -> context manager
- is_locked(path) -> bool
- lock_info(path) -> dict | None
- LockTimeoutError (subclasse de TimeoutError)

DECISÃO SOBRE O CAMINHO PADRÃO
------------------------------
O `path` relativo (ex.: "config.json") é resolvido com
os.path.join(os.path.dirname(os.path.abspath(__file__)), path). Escolhemos o
diretório deste módulo em vez do cwd porque é mais robusto: o robô pode ser
iniciado de qualquer diretório de trabalho e ainda assim proteger o mesmo
arquivo de config (C:\\AIOFEN\\config.json). Caminhos absolutos são usados
como estão. O lock protege o config mesmo que ele ainda não exista — nenhuma
operação é feita sobre o próprio config, apenas sobre o lock file.
"""
import contextlib
import os
import time

import msvcrt

__all__ = [
    "lock_config",
    "is_locked",
    "lock_info",
    "LockTimeoutError",
    "STALE_SECONDS",
]

#: Segundos a partir dos quais um lock é considerado órfão (stale).
#: Se o lock file existir com mtime mais antiga que isso, assumimos que o
#: processo titular morreu (ou abandonou) e quebramos a trava (borramos o
#: arquivo) antes de tentar adquirir — evita trava eterna.
STALE_SECONDS = 5 * 60  # 300 s

#: Tamanho fixo do lock file, em bytes.
LOCK_FILE_SIZE = 256

#: Offset onde começam os metadados (após o byte travado).
_META_START = 1

#: Intervalo de retry da tentativa de lock (segundos).
_RETRY_INTERVAL = 0.1


class LockTimeoutError(TimeoutError):
    """Levantada quando a trava não pode ser adquirida dentro do timeout."""


# --------------------------------------------------------------------------- #
# Utilidades internas
# --------------------------------------------------------------------------- #

def _resolve(path):
    """Converte um path (relativo ou absoluto) em caminho absoluto robusto.

    Relativos são resolvidos a partir do diretório deste módulo, tornando o
    comportamento independente do cwd do processo chamador.
    """
    if not isinstance(path, (str, os.PathLike)):
        raise TypeError("path deve ser str ou os.PathLike")
    p = os.fspath(path)
    if os.path.isabs(p):
        return os.path.abspath(p)
    base = os.path.dirname(os.path.abspath(__file__))
    return os.path.normpath(os.path.join(base, p))


def _lock_path(path):
    """Retorna o caminho do lock file para um dado path de config."""
    return _resolve(path) + ".lock"


def _now():
    return time.time()


def _open_lock_file(lock_path):
    """Abre o lock file em r+b (leitura+escrita no meio do arquivo).

    IMPORTANTE: não usamos 'a+b' porque no Windows o modo append força toda
    escrita para o final do arquivo, o que quebraria a gravação de metadados
    no offset 1. Criamos o arquivo vazio se ele não existir.
    """
    if not os.path.exists(lock_path):
        with open(lock_path, "wb"):
            pass
    return open(lock_path, "r+b", buffering=0)


def _write_meta(handle, pid, ts):
    """Grava metadados (PID + timestamp) no offset 1 do lock file.

    Formato: "v1|pid=<PID>|ts=<EPOCH>\n", preenchido com espaços até o fim.
    """
    line = "v1|pid={}|ts={!r}\n".format(pid, ts)
    payload = line.encode("utf-8", "replace")
    if len(payload) > LOCK_FILE_SIZE - _META_START:
        payload = payload[:LOCK_FILE_SIZE - _META_START]
    handle.seek(_META_START)
    handle.write(payload)
    pad = LOCK_FILE_SIZE - _META_START - len(payload)
    if pad > 0:
        handle.write(b" " * pad)
    handle.flush()
    os.fsync(handle.fileno())


def _read_meta(lock_path):
    """Lê os metadados do lock file a partir do offset 1.

    Retorna dict({"pid", "timestamp"}) ou None (arquivo inexistente, meta
    ilegível ou inválida). Como o byte 0 é o único travado, esta leitura
    funciona mesmo quando outro processo está segurando a trava.
    """
    try:
        with open(lock_path, "rb") as f:
            # Lê a partir do offset 1: o byte 0 é o único travado e fica
            # ilegível enquanto a trava está segurada — o meta não.
            f.seek(_META_START)
            data = f.read(LOCK_FILE_SIZE - _META_START)
    except OSError:
        return None
    head = data.split(b"\n", 1)[0].decode("utf-8", "replace")
    fields = {"pid": None, "timestamp": None}
    for part in head.split("|"):
        if part.startswith("pid="):
            try:
                fields["pid"] = int(part.split("=", 1)[1])
            except (ValueError, IndexError):
                fields["pid"] = None
        elif part.startswith("ts="):
            try:
                fields["timestamp"] = float(part.split("=", 1)[1])
            except (ValueError, IndexError):
                fields["timestamp"] = None
    if fields["pid"] is None:
        return None
    return {"pid": fields["pid"], "timestamp": fields["timestamp"]}


def _is_stale(lock_path):
    """True se o lock file existir e sua mtime for mais antiga que STALE_SECONDS."""
    if not os.path.exists(lock_path):
        return False
    try:
        st = os.stat(lock_path)
    except OSError:
        return False
    return (_now() - st.st_mtime) > STALE_SECONDS


def _break_lock(lock_path):
    """Quebra/borra um lock file órfão.

    Política de stale/force: o arquivo é "borrado" (truncado para 0). Se não
    for possível abrir para truncar (ex.: outro processo segurando com acesso
    exclusivo), tentamos remoção direta via os.remove. Lembrando que no
    Windows a trava de bytes é liberada automaticamente pelo SO quando o
    processo titular morre — a stale detection serve principalmente para
    limpar relíquias de arquivo e impedir a espera eterna por um lock cujo
    dono não existe mais.
    """
    if not os.path.exists(lock_path):
        return False
    try:
        with open(lock_path, "r+b", buffering=0) as f:
            f.truncate(0)
            f.flush()
        return True
    except OSError:
        try:
            os.remove(lock_path)
            return True
        except OSError:
            return False


def _acquire_byte(handle, timeout):
    """Tenta adquirir o lock sobre 1 byte (offset 0) com retry até o timeout.

    Retorna True em sucesso. Levanta LockTimeoutError se exceder o timeout.
    """
    deadline = _now() + timeout
    # Garante que exista pelo menos 1 byte gravável para travar.
    handle.seek(0, os.SEEK_END)
    if handle.tell() < 1:
        handle.seek(0)
        handle.write(b"X")
        handle.flush()
    while True:
        try:
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            return True
        except OSError as exc:
            if _now() >= deadline:
                raise LockTimeoutError(
                    "Não foi possível adquirir a trava em {:.1f}s "
                    "(lock file: {}): {}".format(timeout, handle.name, exc))
            time.sleep(_RETRY_INTERVAL)


def _release_byte(handle):
    """Libera o lock (LK_UNLCK) sobre o byte travado; erros são ignorados."""
    try:
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    except OSError:
        pass


# --------------------------------------------------------------------------- #
# API pública
# --------------------------------------------------------------------------- #

@contextlib.contextmanager
def lock_config(path="config.json", timeout=10.0, force=False):
    """Adquire uma trava exclusiva de escrita sobre o arquivo de config.

    Parâmetros
    ----------
    path : str | os.PathLike
        Caminho do config a proteger (ex.: "config.json"). Relativos são
        resolvidos a partir do diretório deste módulo. O lock file derivado
        é `<path>.lock`. O config em si nunca é aberto — o lock funciona mesmo
        que o config ainda não exista.
    timeout : float
        Segundos máximos de espera pela trava (default 10.0). Timeout <= 0
        tenta apenas uma vez, imediatamente.
    force : bool
        Se True, borra/remove o lock file antes de tentar adquirir (quebra
        imediata da trava existente, além da stale detection).

    Comportamento
    -------------
    - Cria/abre `<path>.lock` (não trunca conteúdo existente não-stale).
    - Se o lock estiver stale (>5min) ou force=True, borra o arquivo antes.
    - Adquire via `msvcrt.locking` (LK_NBLCK) sobre 1 byte, com retry a cada
      ~0.1s até o timeout.
    - Grava metadados (PID + timestamp) dentro do lock file.
    - Ao sair do bloco `with`, libera (LK_UNLCK) e fecha o arquivo.
    - NÃO é reentrante: aquisição aninhada do mesmo lock (mesmo ou outro
      processo) levanta LockTimeoutError.

    Raises
    ------
    LockTimeoutError : trava não adquirida dentro do timeout.
    OSError : falha de E/S ao criar/abrir o lock file.
    """
    resolved = _resolve(path)
    lock_path = resolved + ".lock"

    if force:
        _break_lock(lock_path)

    # Stale detection: lock órfão (mtime > 5min) é quebrado automaticamente.
    if _is_stale(lock_path):
        _break_lock(lock_path)

    f = _open_lock_file(lock_path)
    acquired = False
    try:
        _acquire_byte(f, timeout)
        acquired = True
        try:
            _write_meta(f, os.getpid(), _now())
        except OSError:
            # Metadados são best-effort (auditoria); não cancelam a aquisição.
            pass
        yield resolved
    finally:
        if acquired:
            _release_byte(f)
        try:
            f.close()
        except OSError:
            pass


def is_locked(path="config.json"):
    """Retorna True se a trava estiver ativa (segurada) agora.

    Implementação: tenta travar o byte 0 do lock file com LK_NBLCK. Se
    conseguir, ninguém está segurando (libera e retorna False); se falhar,
    alguém (este processo ou outro) está segurando e retorna True. Lock file
    inexistente => False.
    """
    lock_path = _lock_path(path)
    if not os.path.exists(lock_path):
        return False
    try:
        f = open(lock_path, "r+b", buffering=0)
    except OSError:
        # Não conseguimos abrir: assumimos travado (visão conservadora).
        return True
    try:
        f.seek(0, os.SEEK_END)
        if f.tell() < 1:
            return False  # vazio: nada para travar, logo sem trava
        f.seek(0)
        try:
            msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            return True
        else:
            msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
            return False
    finally:
        try:
            f.close()
        except OSError:
            pass


def lock_info(path="config.json"):
    """Retorna dict com PID e timestamp do titular da trava, ou None.

    Retorna None quando:
        - o lock file não existe;
        - ninguém está segurando a trava no momento (lock livre/órfão);
        - os metadados não puderam ser lidos/interpretados.

    O dict tem a forma {"pid": int, "timestamp": float}. Para saber se há
    trava ativa, use `is_locked`.
    """
    lock_path = _lock_path(path)
    if not os.path.exists(lock_path):
        return None
    if not is_locked(path):
        return None  # ninguém segurando => sem trava => None
    return _read_meta(lock_path)


# --------------------------------------------------------------------------- #
# Auto-teste (rode: python config_lock.py)
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    import tempfile
    tmp = tempfile.mkdtemp(prefix="config_lock_selftest_")
    cfg = os.path.join(tmp, "config_selftest.json")
    print("dir de auto-teste:", tmp)
    print("is_locked (antes):", is_locked(cfg))
    with lock_config(cfg, timeout=2.0):
        print("is_locked (dentro):", is_locked(cfg))
        print("lock_info (dentro):", lock_info(cfg))
    print("is_locked (depois):", is_locked(cfg))
    print("lock_info (depois):", lock_info(cfg))
    os.remove(cfg + ".lock")
    print("auto-teste OK")