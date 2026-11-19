# -*- coding: utf-8 -*-
"""Varredura SOMENTE LEITURA de conteudo sensivel antes do commit do fecho.

Motivo (19/11): o fecho commitava qualquer arquivo da whitelist sem olhar o
conteudo. Um ``relatorio_diario_*.txt`` gerado pelo robo pode trazer numero de
conta e saldo; um ``plano_*.txt`` pode trazer um token colado por engano. O
``commit_dia.executar_commit`` passa a chamar ``varrer`` ANTES do ``git add`` e
nao commita se houver achado.

O que e procurado (e por que):

  - ``conta``: 6+ digitos imediatamente depois de conta/account/login/usuario.
    A exigencia de o numero vir logo apos a palavra (aceitando so ``:``/``=``,
    ``**`` de markdown e a palavra ``demo``) foi medida em 19/11 contra os 170
    arquivos da whitelist: a versao frouxa ("palavra + 6 digitos em 60
    caracteres") gerava 3 falsos positivos no ROADMAP (``magic=123456``,
    ``ticket=2243200971``, ``magic=123457``). A versao estrita acerta as 4
    linhas reais de conta e ignora magic/ticket.
  - ``saldo``: a palavra ``saldo`` e um valor em ``R$`` na MESMA linha. Exigir
    a palavra evita bloquear o ROADMAP inteiro por causa de custos legitimos
    como ``R$ 1,20/contrato``.
  - ``segredo``: password/passwd/senha/token/api_key/secret com valor literal.
    Placeholders (``null``, ``os.environ[...]``, ``***``) nao contam.

Nunca guardamos nem devolvemos o trecho casado: o achado tem apenas
``arquivo``, ``linha`` e ``tipo``. O log do fecho tambem nao imprime o valor.

Este modulo nao escreve nada, nao chama MT5 e nao usa logging. A leitura dos
arquivos staged usa ``git show :caminho`` para conferir o blob do indice, nao
o working tree (que pode ja ter sido corrigido sem ``git add``).
"""
from __future__ import annotations

import os
import re
import subprocess
from typing import Iterable, List, Optional, Sequence

MAX_BYTES = 2 * 1024 * 1024  # 2 MB: maior arquivo da whitelist hoje tem 1.359 B

TIPOS = ("conta", "saldo", "segredo")

_KW_CONTA = r"(?:conta|account|login|usuario|usuário|user)"
_RE_CONTA = re.compile(
    # "Conta: **12345678", "Conta:** demo 12345678", "conta=12345678"
    r"(?i)\b" + _KW_CONTA + r"\b[ \t]*(?:[:=]|[-–—])?[ \t]*"
    r"(?:\*{1,2})?[ \t]*(?:demo[ \t]+)?(?:\*{1,2})?[ \t]*"
    r"(?<!\d)\d{6,}(?!\d)"
    # "12345678 (conta demo)" - forma reversa, tambem estrita
    r"|(?<!\d)\d{6,}(?!\d)[ \t]*\(?[ \t]*" + _KW_CONTA + r"\b"
)
_RE_SALDO = re.compile(
    r"(?i)\bsaldo\b[^\n]{0,80}?R\$\s*\d"
    r"|R\$\s*\d[^\n]{0,80}?\bsaldo\b"
)
_RE_SEGREDO = re.compile(
    r"(?i)\b(password|passwd|senha|token|api[_-]?key|apikey|secret|"
    r"client[_-]?secret)\b[\"']?\s*[:=]\s*([\"']?)([^\s\"',;]{4,})\2"
)

_PLACEHOLDERS = {
    "null", "none", "true", "false", "undefined", "nan", "***", "...",
    "xxxx", "changeme", "troque", "redacted", "placeholder",
}


def _valor_parece_segredo(valor: str) -> bool:
    """True se o valor capturado parece um segredo literal (nao placeholder)."""
    v = (valor or "").strip().strip("\"'")
    if len(v) < 4:
        return False
    baixo = v.lower()
    if baixo in _PLACEHOLDERS:
        return False
    if any(p in baixo for p in ("aqui", "here", "exemplo", "example")):
        return False
    if baixo.startswith(("os.", "self.", "this.", "process.env", "$", "{",
                         "<", "(", "[")):
        return False
    if len(set(v)) == 1:  # "****", "xxxx", "0000"
        return False
    return True


def analisar_texto(texto: str, arquivo: str = "") -> List[dict]:
    """Achados de um texto. Devolve ``[{arquivo, linha, tipo}]`` sem o valor."""
    achados: List[dict] = []
    vistos = set()
    for numero, linha in enumerate((texto or "").splitlines(), start=1):
        for tipo, regex in (("conta", _RE_CONTA), ("saldo", _RE_SALDO)):
            if regex.search(linha) and (numero, tipo) not in vistos:
                vistos.add((numero, tipo))
                achados.append({"arquivo": arquivo, "linha": numero,
                                "tipo": tipo})
        for m in _RE_SEGREDO.finditer(linha):
            if (numero, "segredo") in vistos:
                break
            if _valor_parece_segredo(m.group(3)):
                vistos.add((numero, "segredo"))
                achados.append({"arquivo": arquivo, "linha": numero,
                                "tipo": "segredo"})
                break
    return achados


def _decodificar(dados: bytes) -> Optional[str]:
    """Texto UTF-8 tolerante; ``None`` para binario ou arquivo grande demais."""
    if dados is None or len(dados) > MAX_BYTES:
        return None
    if b"\x00" in dados[:8192]:
        return None
    return dados.decode("utf-8", errors="replace")


def analisar_arquivo(caminho: str, arquivo: Optional[str] = None) -> List[dict]:
    """Le o arquivo do disco (somente leitura) e devolve os achados."""
    try:
        with open(caminho, "rb") as f:
            dados = f.read(MAX_BYTES + 1)
    except OSError:
        return []
    texto = _decodificar(dados)
    if texto is None:
        return []
    return analisar_texto(texto, arquivo or caminho)


def _git_bytes(base_dir: str, args: Sequence[str], timeout: float = 30):
    try:
        return subprocess.run(["git", "-C", base_dir] + list(args),
                              capture_output=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return None


def arquivos_staged(base_dir: str) -> List[str]:
    """Caminhos no indice (adicionados/modificados/renomeados), em '/'."""
    proc = _git_bytes(base_dir, ["diff", "--cached", "--name-only",
                                 "--diff-filter=ACMR", "-z"])
    if proc is None or proc.returncode != 0 or not proc.stdout:
        return []
    partes = proc.stdout.split(b"\x00")
    return sorted(p.decode("utf-8", errors="replace").replace("\\", "/")
                  for p in partes if p)


def ler_staged(base_dir: str, caminho: str) -> Optional[bytes]:
    """Conteudo do blob no indice (``git show :caminho``), nao do disco."""
    proc = _git_bytes(base_dir, ["show", ":" + caminho])
    if proc is None or proc.returncode != 0:
        return None
    return proc.stdout


def varrer(base_dir: str, arquivos: Iterable[str] = (),
           incluir_staged: bool = True) -> List[dict]:
    """Achados nos arquivos indicados (disco) e no que estiver staged.

    ``arquivos`` sao caminhos relativos a ``base_dir`` (como a whitelist do
    fecho os devolve). A varredura do indice cobre ate arquivos fora da
    whitelist que um humano tenha deixado staged: o commit do fecho e restrito,
    mas a barreira de conteudo e fail-closed.
    """
    achados: List[dict] = []
    vistos = set()

    def _adicionar(lista):
        for item in lista:
            chave = (item["arquivo"], item["linha"], item["tipo"])
            if chave not in vistos:
                vistos.add(chave)
                achados.append(item)

    for rel in arquivos or ():
        rel = str(rel).replace("\\", "/")
        caminho = os.path.join(base_dir, rel.replace("/", os.sep))
        _adicionar(analisar_arquivo(caminho, arquivo=rel))

    if incluir_staged:
        for rel in arquivos_staged(base_dir):
            dados = ler_staged(base_dir, rel)
            if dados is None:
                # indice ilegivel para este caminho: cai para o disco
                _adicionar(analisar_arquivo(
                    os.path.join(base_dir, rel.replace("/", os.sep)),
                    arquivo=rel))
                continue
            texto = _decodificar(dados)
            if texto is not None:
                _adicionar(analisar_texto(texto, arquivo=rel))

    return sorted(achados, key=lambda a: (a["arquivo"], a["linha"],
                                          a["tipo"]))


def formatar(achados: Iterable[dict]) -> List[str]:
    """``arquivo:linha (tipo)`` - nunca inclui o valor encontrado."""
    return [f"{a['arquivo']}:{a['linha']} ({a['tipo']})" for a in achados]
