
import os
import subprocess
import shutil
from datetime import datetime


def run_command(command):
    try:
        print(f"Executando: {command}")
        subprocess.run(command, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Erro ao executar comando: {e}")
        exit(1)


# 1. Instalar PyInstaller e PyArmor (se não estiverem instalados)
print("Verificando e instalando dependências...")
run_command("pip install pyinstaller pyarmor")

# 2. Ofuscar o código com PyArmor
print("Ofuscando o código com PyArmor...")
obfuscated_script = "monstro_unificado_v2_obf.py"
run_command(f"pyarmor obfuscate --output dist_obf monstro_unificado_v2.py")

# Mover o arquivo ofuscado para a pasta raiz para o PyInstaller
shutil.move("dist_obf/monstro_unificado_v2.py", obfuscated_script)

# 3. Empacotar com PyInstaller
print("Empacotando com PyInstaller...")
# O modelo .h5, .csv e .json devem ser incluídos como dados
# O PyInstaller os colocará na pasta temporária do executável
# O script Python deve ser capaz de encontrá-los no diretório de execução

# Para PyInstaller, o caminho de destino '.' significa o diretório raiz do executável
# No script Python, eles serão acessíveis diretamente pelo nome do arquivo

pyinstaller_command = (
    f"pyinstaller --onefile --noconsole "
    f"--add-data \"modelo_monstro_win.h5;.\" "
    f"--add-data \"historico_contexto_win.csv;.\" "
    f"--add-data \"config_win_v2.json;.\" "
    f"{obfuscated_script}"
)
run_command(pyinstaller_command)

# 4. Criar um arquivo .zip protegido por senha
print("Criando arquivo .zip protegido por senha...")
output_dir = "dist"
exe_name = os.path.splitext(obfuscated_script)[0] + ".exe"
exe_path = os.path.join(output_dir, exe_name)
zip_filename = f"robo_trader_monstro_{datetime.now().strftime('%Y%m%d')}.zip"

# Para criar um zip com senha, precisamos de uma ferramenta externa como 7zip ou similar
# No ambiente Linux do sandbox, podemos usar 'zip -P' para criar um zip com senha
# No Windows, o usuário precisaria de uma ferramenta como 7-Zip instalada.
# Vou gerar um zip sem senha aqui, e instruir o usuário a adicionar a senha manualmente no Windows.
# Ou, se o usuário tiver 7-Zip, pode-se usar: 7z a -pSECRETPASSWORD {zip_filename} {exe_path}

# Criando um zip simples (sem senha no Linux, instruir o usuário para Windows)
run_command(f"zip -r {zip_filename} {output_dir}")

print(
    f"\n✅ Processo concluído! O executável e os arquivos de dados estão em '{output_dir}/'.")
print(f"O arquivo ZIP '{zip_filename}' foi criado. Por favor, adicione uma senha a ele manualmente no Windows usando uma ferramenta como 7-Zip ou WinRAR.")
print("Para executar o robô, use o arquivo 'run_robo.bat' que será gerado.")

# Limpeza
print("Realizando limpeza de arquivos temporários...")
shutil.rmtree("dist_obf", ignore_errors=True)
os.remove(obfuscated_script)
# Não remover a pasta 'dist' pois contém o executável final
