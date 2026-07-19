#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para corrigir o dashboard HTML
"""


def corrigir_dashboard():
    """Corrige o dashboard HTML que está quebrado."""

    with open("mostro _unificado_copia_do_v2.py", 'r', encoding='utf-8') as f:
        codigo = f.read()

    # Encontra o início e fim da seção HTML
    inicio_html = codigo.find('return """ < !DOCTYPE html >')
    fim_html = codigo.find('"""', inicio_html + 10)

    if inicio_html == -1 or fim_html == -1:
        print("Seção HTML não encontrada")
        return False

    # HTML corrigido e simplificado
    html_corrigido = '''return """<!DOCTYPE html>
<html>
<head>
<title>Monstro Dashboard</title>
<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
<script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
<style>
body {font-family: Arial, sans-serif; margin: 20px;}
.grid {display: grid; grid-template-columns: 1fr 1fr; gap: 20px;}
.card {border: 1px solid #ddd; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);}
.full-width {grid-column: 1 / -1;}
.status {padding: 10px; border-radius: 5px; margin: 10px 0;}
.status.active {background-color: #d4edda; color: #155724;}
.status.inactive {background-color: #f8d7da; color: #721c24;}
.metric {font-size: 24px; font-weight: bold; color: #007bff;}
.chart {height: 300px; margin: 10px 0;}
button {padding: 10px 20px; margin: 5px; border: none; border-radius: 5px; cursor: pointer;}
.btn-primary {background-color: #007bff; color: white;}
.btn-danger {background-color: #dc3545; color: white;}
</style>
</head>
<body>
<h1>Monstro Dashboard - Trading WIN</h1>
<div class="grid">
<div class="card">
<h2>Status do Sistema</h2>
<div id="status" class="status">Carregando...</div>
<div>Lucro Total: <span id="lucro-total" class="metric">R$ 0,00</span></div>
<div>Operações Hoje: <span id="ops-hoje" class="metric">0</span></div>
</div>
<div class="card">
<h2>Performance</h2>
<div id="chart-performance" class="chart"></div>
</div>
<div class="card">
<h2>Distribuição de Scores</h2>
<div id="chart-scores" class="chart"></div>
</div>
<div class="card">
<h2>Progresso do Aprendizado</h2>
<div id="chart-learning" class="chart"></div>
</div>
<div class="card full-width">
<h2>Controles</h2>
<button class="btn-primary" onclick="updateCharts()">Atualizar</button>
<button class="btn-danger" onclick="alert('Função não implementada')">Parar Sistema</button>
</div>
</div>
<script>
function updateCharts() {
    fetch('/api/performance')
        .then(response => response.json())
        .then(data => {
            document.getElementById('lucro-total').textContent = 'R$ ' + (data.lucros.reduce((a,b) => a+b, 0) || 0).toFixed(2);
            document.getElementById('ops-hoje').textContent = data.lucros.length || 0;

            Plotly.newPlot('chart-performance', [{
                x: data.lucros.map((_, i) => i),
                y: data.lucros,
                type: 'scatter',
                mode: 'lines+markers',
                name: 'Lucro'
            }], {title: 'Performance'});
        })
        .catch(error => console.error('Erro:', error));

    fetch('/status')
        .then(response => response.json())
        .then(data => {
            const statusDiv = document.getElementById('status');
            statusDiv.textContent = data.status || 'Desconhecido';
            statusDiv.className = 'status ' + (data.ativo ? 'active' : 'inactive');
        })
        .catch(error => console.error('Erro:', error));
}
setInterval(updateCharts, 5000);
updateCharts();
</script>
</body>
</html>
"""'''

    # Substitui a seção HTML
    codigo_corrigido = codigo[:inicio_html] + \
        html_corrigido + codigo[fim_html + 3:]

    # Salva o arquivo corrigido
    with open("mostro _unificado_copia_do_v2.py", 'w', encoding='utf-8') as f:
        f.write(codigo_corrigido)

    print("Dashboard HTML corrigido com sucesso!")
    return True


if __name__ == "__main__":
    corrigir_dashboard()
