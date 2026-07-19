#!/usr/bin/env python3
""
ipt robusto para corrigir TODOS os problemas de indent
"""

def fix_python_indentation(input_file, output_file):
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.split('\n')
fixed_lines = []

    for i, line in enumerate(lines):
        # Remove trailing whitespace
        line = line.rstrip()

ip empty lines
        if not line.strip():
s.append('')
            continue

        # Count leadingces
        leading_spaces = len(line) - len(line.lstrip())

        # Fix specific problematic patterns
        stripped = lin

        # Global variable declarations should not be indented
        if (strippetartswith('MT5_PATH =') or
            stripped.startswith('SYMBOL =') or
            stripped.startswith('TIMEFRAME =') or
            stripped.startswith('HISTORICO_CSV =') or
            stripped.startswith('MODELO_PATH =') or
            stripped.startswith('LOG_FILE =') o
     stripped.startswith('PORT =') or
            stripped.startswith('DEBUG =') or
            stripped.startswith('MIC_NUMBER =') or
            stripped.startswith('VOLUME_MINIMO =') or
            stripped.startswith('N_FEATURES =') or
            stripped.startswith('DEVIATION =') or
            stripped.startswith('TICK_SIZE =') or
            stripped.startswith('TICKS_POR_PONTO =') or
            stripped.startswith('VOLUME_PADRAO =') or
            stripped.startswith('HORARIO_') or
            stripped.startswith('DIGITS_INDICE =') or
            stripped.startswith('MIN_TICKS =') or
            stripped.startswith('MAX_TICKS =') or
            stripped.startswith('MAX_DISTANCIA_') or
            stripped.startswith('TRAILING_') or
            stripped.startswith('SL_POINTS =') or
            stripped.startswith('TP_POINTS =') or
            stripped.startswith('MAX_LOSS_') or
            stripped.startswith('MAX_DRAWDOWN =') or
            stripped.startswith('MAX_SPREAD =') or
            stripped.startswith('MIN_TICKS_VALIDOS =') or
            stripped.startswith('MIN_VOLUME_BOOK =') or
            stripped.startswith('MIN_EXPERIENCIAS_') or
            stripped.startswith('MAX_EXPERIENCIAS_') or
            stripped.startswith('EPOCHS_TREINO =') or
            stripped.startswith('BATCH_SIZE =') or
            stripped.startswith('MIN_DELTA_LOSS =') or
            stripped.startswith('PATIENCE_') or
            stripped.startswith('DECAY_') or
            stripped.startswith('INTERVALO_') or
            stripped.startswith('PESO_') or
            stripped.startswith('JANELA_') or
            stripped.startswith('INVERSAO_') or
            stripped.startswith('SCORE_') or
            stripped.startswith('TEMPO_') or
            stripped.startswith('THRESHOLD_') or
            stripped.startswith('MULTIPLICADOR_') or
            stripped.startswith('PERIODO_') or
            stripped.startswith('SL_MAX_') or
            stripped.startswith('TP_MAX_') or
            stripped.startswith('MIN_RATIO_') or
            stripped.startswith('MAX_LOSSES_') or
            stripped.startswith('CICLOS_') or
            stripped.startswith('MIN_LUCRO_') or
            stripped.startswith('BALANCEAMENTO_') or
            stripped.startswith('AJUSTE_') or
            stripped.startswith('MODO_') or
            stripped.startswith('VOLUME_') or
            stripped.startswith('CIRCUIT_') or
            stripped.startswith('SPREAD_') or
            stripped.startswith('LOSS_') or
            stripped.startswith('SAIDA_') or
            stripped.startswith('RSI_') or
            stripped.startswith('CONFIG_FILE =') or
            stripped.startswith('config =') or
            stripped.startswith('CACHE_TTL =') or
            stripped.startswith('MAX_RETRY_') or
            stripped.startswith('RETRY_WAIT_') or
            stripped.startswith('trailing_stop =') or
            stripped.startswith('balanceador =') or
            stripped.startswith('detector_modo =') or
            stripped.startswith('circuit_breaker =') or
            stripped.startswith('saida_inteligente =')):
            fixed_lines.append(stripped)
            continue

        # Function definitions at module level
        if stripped.startswith('def ') and not line.startswith('    '):
            fixed_lines.append(stripped)
            continue

        # Class definitions at module level
        if stripped.startswith('class ') and not line.startswith('    '):
            fixed_lines.append(stripped)
            continue

        # Comments and docstrings
        if stripped.startswith('#') or stripped.startswith('"""') or stripped.startswith("'''"):
            # Keep original indentation for comments
            fixed_lines.append(line)
            continue

        # Method definitions inside classes (should have 4 spaces)
        if stripped.startswith('def ') and i > 0:
            # Check if we're inside a class
            in_class = False
            for j in range(i-1, -1, -1):
                prev_line = lines[j].strip()
                if prev_line.startswith('class '):
                    in_class = True
                    break
                elif prev_line.startswith('def ') and not lines[j].startswith('    '):
                    break

            if in_class:
                fixed_lines.append('    ' + stripped)
                continue

        # Code inside methods/functions (should have 8+ spaces)
        if stripped and i > 0:
            # Check if previous non-empty line was a function/method definition
            for j in range(i-1, -1, -1):
                prev_line = lines[j].strip()
                if not prev_line:
                    continue
                if prev_line.endswith(':') and ('def ' in prev_line or 'class ' in prev_line):
                    # This should be indented
                    if lines[j].startswith('    '):  # Method in class
                        fixed_lines.append('        ' + stripped)
                    else:  # Function at module level
                        fixed_lines.append('    ' + stripped)
                    break
                else:
                    # Keep original line
                    fixed_lines.append(line)
                    break
            else:
                fixed_lines.append(line)
        else:
            fixed_lines.append(line)

    # Write fixed content
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(fixed_lines))

    print(f"Fixed indentation saved to: {output_file}")

if __name__ == "__main__":
    fix_python_indentation("mostro _unificado_copia_do_v2.py", "mostro_unificado_fixed.py")
