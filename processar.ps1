$path = "C:\AIOFEN\logs\modelo_a_shadow.csv"
$data = Import-Csv -Path $path -Delimiter ','
$ci = [System.Globalization.CultureInfo]::InvariantCulture

$start = [datetime]"2026-08-01 00:00:00"
$end   = [datetime]"2026-10-30 23:59:59"

$filtered = $data | Where-Object {
    $ts = [datetime]$_.timestamp
    $ts -ge $start -and $ts -le $end
}
$total = $filtered.Count

# registros com resultado, acrescente coluna numerica ptsNum para comparacoes confiaveis
$withResult = $filtered | Where-Object { -not [string]::IsNullOrWhiteSpace($_.resultado_bruto) } |
    Select-Object *, @{N='ptsNum';E={[double]::Parse($_.resultado_bruto,[System.Globalization.NumberStyles]::Float,$ci)}}
$withoutResult = $filtered | Where-Object { [string]::IsNullOrWhiteSpace($_.resultado_bruto) }

$gains = $withResult | Where-Object { $_.ptsNum -gt 0 }
$losses = $withResult | Where-Object { $_.ptsNum -lt 0 }
$zeros = $withResult | Where-Object { $_.ptsNum -eq 0 }

$gainPts = ($gains | Measure-Object -Property ptsNum -Sum).Sum
$lossPts = ($losses | Measure-Object -Property ptsNum -Sum).Sum
$netPts = ($withResult | Measure-Object -Property ptsNum -Sum).Sum

$gainRs = $gainPts * 10
$lossRs = $lossPts * 10
$netRs = $netPts * 10

$winRate = if ($withResult.Count -gt 0) { $gains.Count / $withResult.Count * 100 } else { 0 }

$sb = New-Object System.Text.StringBuilder
$sb.AppendLine("# Relatório - Modelo A Shadow (01/08/2026 a 30/10/2026)") | Out-Null
$sb.AppendLine("") | Out-Null
$sb.AppendLine("## Resumo") | Out-Null
$sb.AppendLine("") | Out-Null
$sb.AppendLine("- Total de registros no período: $total") | Out-Null
$sb.AppendLine("- Registros com resultado (nao vazios): $($withResult.Count)") | Out-Null
$sb.AppendLine("- Registros sem resultado (vazios): $($withoutResult.Count)") | Out-Null
$sb.AppendLine("- Total de ganhos: $($gains.Count) registros | $([math]::Round($gainPts,1)) pts | R$ $([math]::Round($gainRs,2))") | Out-Null
$sb.AppendLine("- Total de perdas: $($losses.Count) registros | $([math]::Round($lossPts,1)) pts | R$ $([math]::Round($lossRs,2))") | Out-Null
$sb.AppendLine("- Resultado liquido: $([math]::Round($netPts,1)) pts | R$ $([math]::Round($netRs,2))") | Out-Null
$sb.AppendLine("- Win rate: $([math]::Round($winRate,2))%") | Out-Null
$sb.AppendLine("") | Out-Null
$sb.AppendLine("## Tabela Completa de Registros") | Out-Null
$sb.AppendLine("") | Out-Null
$sb.AppendLine("| # | Data | Hora | Ticket | Direção | Prob. Modelo A | Resultado (pts) | Resultado (R$) |") | Out-Null
$sb.AppendLine("|---|------|------|--------|---------|----------------|-----------------|----------------|") | Out-Null

$i = 0
foreach ($r in $filtered) {
    $i++
    $ts = [datetime]$r.timestamp
    $dataFmt = $ts.ToString("dd/MM/yyyy")
    $hora = $ts.ToString("HH:mm:ss")
    $ptsRaw = $r.resultado_bruto
    if ([string]::IsNullOrWhiteSpace($ptsRaw)) {
        $ptsStr = "--"
        $rsStr = "--"
    } else {
        $pts = [double]::Parse($ptsRaw,[System.Globalization.NumberStyles]::Float,$ci)
        $ptsStr = $pts.ToString("0.0", $ci)
        $rsStr = "R$ " + ($pts * 10).ToString("0.00", $ci)
    }
    $prob = [double]::Parse($r.prob_modelo_a,[System.Globalization.NumberStyles]::Float,$ci)
    $sb.AppendLine("| $i | $dataFmt | $hora | $($r.ticket_mt5) | $($r.direcao) | $($prob.ToString("0.0000", $ci)) | $ptsStr | $rsStr |") | Out-Null
}

$sb.AppendLine("") | Out-Null
$sb.AppendLine("Nota: 1 ponto = R$ 10,00. Coluna usada: resultado_bruto (a coluna resultado_pontos esta vazia no arquivo).") | Out-Null

$sb.ToString() | Set-Content -Path "C:\AIOFEN\relatorio_modelo_a_shadow.md" -Encoding UTF8

Write-Host ("Concluido. Total={0} ComResultado={1} SemResultado={2} Ganhos={3} Perdas={4} Zeros={5} NetPts={6:F1} NetRs={7:F2} WinRate={8:F2}%" -f $total,$withResult.Count,$withoutResult.Count,$gains.Count,$losses.Count,$zeros.Count,$netPts,$netRs,$winRate)
