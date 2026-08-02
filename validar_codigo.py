"""
VALIDAR CÓDIGO — Atualiza o hash de integridade após alteração intencional.

USO: python validar_codigo.py
     (roda py_compile + atualiza .codigo_hash)

Isso libera o robô para iniciar na próxima execução.
"""
import hashlib
import os
import py_compile
import sys

ARQUIVO_PY = os.path.join(os.path.dirname(
    os.path.abspath(__file__)), "monstro_unificado_v2.py")
ARQUIVO_HASH = os.path.join(os.path.dirname(
    os.path.abspath(__file__)), ".codigo_hash")


def main():
    print("=" * 50)
    print("🔐 VALIDAÇÃO DO CÓDIGO — MONSTRO V2")
    print("=" * 50)

    # 1. Verifica sintaxe com py_compile
    print("\n📋 Etapa 1: Verificando sintaxe (py_compile)...")
    try:
        py_compile.compile(ARQUIVO_PY, doraise=True)
        print("   ✅ Sintaxe OK — sem erros de compilação")
    except py_compile.PyCompileError as e:
        print(f"   ❌ ERRO DE SINTAXE DETECTADO!")
        print(f"   {e}")
        print("\n⛔ Hash NÃO atualizado. Corrija o erro antes.")
        sys.exit(1)

    # 2. Calcula e salva novo hash
    print("\n📋 Etapa 2: Atualizando hash de integridade...")
    with open(ARQUIVO_PY, "rb") as f:
        hash_novo = hashlib.md5(f.read()).hexdigest()

    # Mostra hash anterior se existir
    if os.path.exists(ARQUIVO_HASH):
        with open(ARQUIVO_HASH, "r") as f:
            hash_anterior = f.read().strip()
        if hash_anterior == hash_novo:
            print(f"   ℹ️ Hash não mudou: {hash_novo[:16]}...")
            print("   (código não foi alterado desde a última validação)")
        else:
            print(f"   Hash anterior: {hash_anterior[:16]}...")
            print(f"   Hash novo:     {hash_novo[:16]}...")
    else:
        print(f"   Hash gerado: {hash_novo[:16]}...")

    with open(ARQUIVO_HASH, "w") as f:
        f.write(hash_novo)

    print("\n" + "=" * 50)
    print("✅ CÓDIGO VALIDADO E LIBERADO!")
    print("   O robô pode iniciar normalmente.")
    print("=" * 50)


if __name__ == "__main__":
    main()
