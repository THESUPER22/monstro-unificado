# -*- coding: utf-8 -*-
"""
Testes do utilitário de trava única de escrita: C:\\AIOFEN\\config_lock.py

Roda com pytest OU diretamente como script (stdlib puro):
    python -m venv ... (opcional)
    python -m pytest tests/teste_config_lock.py -v        # se pytest existir
    python tests/teste_config_lock.py                     # sem pytest (asserts puros)

Todos os testes usam diretórios temporários (tempfile) e caminhos com
"config_test.json" — NUNCA tocam no `config.json` real do projeto,
nem em `logs/`, nem nos robôs existentes.

POLÍTICA DE REENTRÂNCIA ESCOLHIDA
---------------------------------
**Não reentrante.** Uma segunda aquisição da MESMA trava enquanto ela já está
segurada — seja pelo MESMO processo (aquisição aninhada) seja por outro
processo — sempre levanta `LockTimeoutError`. Motivo: a trava representa uma
única operação de escrita no config por vez; permitir reentrância criaria
ambiguidade sobre quem escreve e poderia mascarar bugs de edição concorrente.
Esta política é consistente com o comportamento nativo do Windows/msvcrt
(região já travada não pode ser re-travada, mesmo pelo mesmo processo) e é
testada explicitamente abaixo (teste 2 e teste 4).
"""
import os
import shutil
import subprocess
import sys
import tempfile
import time

# Garante que `config_lock` seja importável tanto via pytest (cwd = C:\AIOFEN)
# quanto via execução direta (python tests/teste_config_lock.py).
_PKG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PKG_DIR not in sys.path:
    sys.path.insert(0, _PKG_DIR)

from config_lock import (  # noqa: E402
    lock_config,
    is_locked,
    lock_info,
    LockTimeoutError,
    _resolve,
)

# Intervalo de polling interno usado nos testes.
_POLL = 0.05


def _novo_tmp():
    """Cria um diretório temporário próprio do teste. Retorna (tmp, cfg)."""
    tmp = tempfile.mkdtemp(prefix="teste_config_lock_")
    cfg = os.path.join(tmp, "config_test.json")
    return tmp, cfg


def _limpa(tmp, cfg):
    if os.path.exists(cfg + ".lock"):
        try:
            os.remove(cfg + ".lock")
        except OSError:
            pass
    shutil.rmtree(tmp, ignore_errors=True)


def _fabrica_lock_orfao(cfg, pid_fake=999999, idade_segundos=6 * 60):
    """Cria um lock file com o formato do config_lock, mas com mtime antigo.

    Simula um lock órfão: já existia, com PID "morto", e nunca foi renovado.
    """
    lock_path = cfg + ".lock"
    payload = b"X" + "v1|pid={}|ts=1.0\n".format(pid_fake).encode("utf-8")
    payload += b" " * (256 - len(payload))
    with open(lock_path, "wb") as f:
        f.write(payload)
    antigo = time.time() - idade_segundos
    os.utime(lock_path, (antigo, antigo))
    return lock_path


# --------------------------------------------------------------------------- #
# Testes
# --------------------------------------------------------------------------- #

def test_1_trava_adquire_e_libera():
    tmp, cfg = _novo_tmp()
    try:
        assert not is_locked(cfg), "não deveria estar travado antes"
        with lock_config(cfg, timeout=2.0):
            assert is_locked(cfg), "is_locked deve ser True dentro do lock"
        assert not is_locked(cfg), "is_locked deve ser False após sair do lock"
    finally:
        _limpa(tmp, cfg)


def test_2_segunda_aquisicao_outro_processo_leva_timeout():
    """Outro processo segurando a trava -> LockTimeoutError na nossa tentativa."""
    tmp, cfg = _novo_tmp()
    worker = (
        "import sys, time\n"
        "sys.path.insert(0, {!r})\n"
        "from config_lock import lock_config\n"
        "with lock_config(sys.argv[1], timeout=10.0):\n"
        "    time.sleep(float(sys.argv[2]))\n"
    ).format(_PKG_DIR)
    hold = 2.0
    proc = subprocess.Popen(
        [sys.executable, "-c", worker, cfg, str(hold)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        # Espera o worker segurar a trava de verdade (evita corrida de início).
        deadline = time.time() + 4.0
        while not is_locked(cfg):
            if proc.poll() is not None:
                out, err = proc.communicate()
                raise AssertionError(
                    "worker morreu antes de segurar a trava: {!r}".format(err))
            if time.time() > deadline:
                raise AssertionError("worker não segurou a trava a tempo")
            time.sleep(_POLL)

        t0 = time.time()
        try:
            with lock_config(cfg, timeout=0.5, force=False):
                raise AssertionError(
                    "segunda aquisição deveria levantar LockTimeoutError")
        except LockTimeoutError:
            pass
        elapsed = time.time() - t0
        assert elapsed >= 0.45, (
            "LockTimeoutError veio cedo demais (%.3fs) — trava não respeitada?" % elapsed)

        # Depois que o worker libera, conseguimos adquirir normalmente.
        proc.communicate(timeout=10)
        assert proc.returncode == 0, "worker falhou (rc=%s)" % proc.returncode
        with lock_config(cfg, timeout=2.0, force=False):
            assert is_locked(cfg)
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.communicate()
        _limpa(tmp, cfg)


def test_3_stale_lock_e_quebrado_automaticamente():
    """force=False + lock órfão (mtime 6min atrás) -> trava é quebrada."""
    tmp, cfg = _novo_tmp()
    try:
        _fabrica_lock_orfao(cfg, pid_fake=424242, idade_segundos=6 * 60)
        assert os.path.exists(cfg + ".lock")
        with lock_config(cfg, timeout=0.5, force=False) as resolvido:
            assert os.path.abspath(resolvido) == os.path.abspath(cfg)
            assert is_locked(cfg), "deve conseguir a trava apesar do lock órfão"
            info = lock_info(cfg)
            assert info is not None, "lock_info deveria trazer os metadados novos"
            assert info["pid"] == os.getpid(), (
                "meta deveria ter sido reescrita com o PID atual, veio %r" % info["pid"])
            assert info["timestamp"] > time.time() - 300, (
                "timestamp deveria ser recente (stale foi reescrito), veio %r"
                % info["timestamp"])
        assert not is_locked(cfg)
    finally:
        _limpa(tmp, cfg)


def test_4_aquisicao_aninhada_mesmo_processo_e_recusada():
    """Reentrância recusada: nested no MESMO processo também levanta timeout."""
    tmp, cfg = _novo_tmp()
    try:
        assert not is_locked(cfg)
        with lock_config(cfg, timeout=2.0) as r1:
            assert os.path.abspath(r1) == os.path.abspath(cfg)
            assert is_locked(cfg)
            try:
                with lock_config(cfg, timeout=0.5, force=False):
                    raise AssertionError(
                        "aquisição aninhada deveria levantar LockTimeoutError")
            except LockTimeoutError:
                pass
            # O lock externo continua válido e segurando:
            assert is_locked(cfg), "lock externo deveria continuar ativo"
            info = lock_info(cfg)
            assert info is not None and info["pid"] == os.getpid()
        assert not is_locked(cfg), "após sair, trava deve estar livre"
    finally:
        _limpa(tmp, cfg)


def test_5_lock_info_pid_dentro_e_none_fora():
    tmp, cfg = _novo_tmp()
    try:
        assert lock_info(cfg) is None, "sem trava deve retornar None"
        with lock_config(cfg, timeout=2.0):
            info = lock_info(cfg)
            assert info is not None, "dentro da trava devemos ler os metadados"
            assert info["pid"] == os.getpid(), (info, os.getpid())
            assert isinstance(info["timestamp"], float)
        assert lock_info(cfg) is None, "fora da trava deve retornar None"
    finally:
        _limpa(tmp, cfg)


def test_6_caminho_padrao_resolvido_relativo_ao_modulo():
    """Decisão documentada: path relativo resolve em relação ao diretório do módulo."""
    import config_lock
    esperado = os.path.normpath(
        os.path.join(os.path.dirname(os.path.abspath(config_lock.__file__)),
                     "config.json"))
    assert _resolve("config.json") == esperado
    # Não pode depender do cwd (robustez):
    antigo = os.getcwd()
    try:
        os.chdir(tmpdir := tempfile.mkdtemp(prefix="teste_config_lock_chdir_"))
        try:
            assert _resolve("config.json") == esperado
        finally:
            _limpa(tmpdir, os.path.join(tmpdir, "config_test.json"))
    finally:
        os.chdir(antigo)


# --------------------------------------------------------------------------- #
# Runner standalone (sem pytest)
# --------------------------------------------------------------------------- #

def _main():
    testes = [
        ("T1 aquisição/liberação", test_1_trava_adquire_e_libera),
        ("T2 timeout cross-processo", test_2_segunda_aquisicao_outro_processo_leva_timeout),
        ("T3 stale lock quebrado", test_3_stale_lock_e_quebrado_automaticamente),
        ("T4 reentrância recusada", test_4_aquisicao_aninhada_mesmo_processo_e_recusada),
        ("T5 lock_info pid/None", test_5_lock_info_pid_dentro_e_none_fora),
        ("T6 resolução de path", test_6_caminho_padrao_resolvido_relativo_ao_modulo),
    ]
    falhas = 0
    for nome, fn in testes:
        try:
            fn()
            print("PASS  %s" % nome)
        except Exception as exc:  # noqa: BLE001
            falhas += 1
            print("FAIL  %s -> %r" % (nome, exc))
    print("-" * 50)
    if falhas:
        print("%d/%d testes FALHARAM." % (falhas, len(testes)))
        return 1
    print("Todos os %d testes passaram." % len(testes))
    return 0


if __name__ == "__main__":
    sys.exit(_main())