#!/usr/bin/env python3
import re


def fix_indentation(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    fixed_lines = []

    for i, line in enumerate(lines):
        original_line = line

        # Remove trailing whitespace
        line = line.rstrip() + '\n'

        # Skip empty lines
        if not line.strip():
            fixed_lines.append(line)
            continue

        # Count leading spaces
        leading_spaces = len(line) - len(line.lstrip())

        # If line has content and wrong indentation
        if line.strip():
            # Check if previous line ends with colon (function/class/if/etc definition)
            if i > 0 and lines[i-1].strip().endswith(':'):
                # This line should be indented
                if leading_spaces == 0:
                    line = '    ' + line.lstrip()
                elif leading_spaces % 4 != 0:
                    # Fix to nearest multiple of 4, minimum 4
                    new_indent = max(4, ((leading_spaces + 3) // 4) * 4)
                    line = ' ' * new_indent + line.lstrip()
            else:
                # Normal line - fix to multiple of 4 if needed
                if leading_spaces > 0 and leading_spaces % 4 != 0:
                    new_indent = (leading_spaces // 4) * 4
                    if new_indent == 0 and leading_spaces > 0:
                        new_indent = 4
                    line = ' ' * new_indent + line.lstrip()

        fixed_lines.append(line)

    # Write back
    with open(filename, 'w', encoding='utf-8') as f:
        f.writelines(fixed_lines)

    print(f"Fixed indentation in {filename}")


if __name__ == "__main__":
    fix_indentation("mostro _unificado_copia_do_v2.py")
