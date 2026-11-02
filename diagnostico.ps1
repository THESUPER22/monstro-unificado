$ci = [System.Globalization.CultureInfo]::InvariantCulture
function ParseDbl($v) { [double]::Parse($v, [System.Globalization.NumberStyles]::Float, $ci) }
$d = Import-Csv C:\AIOFEN\logs\modelo_a_shadow.csv -Delimiter ','
$w = $d | Where-Object { [string]::IsNullOrWhiteSpace($_.resultado_bruto) -eq $false }
Write-Host ("Total=" + $d.Count)
Write-Host ("withResult=" + $w.Count)
Write-Host ("withoutResult=" + ($d.Count - $w.Count))
$g = $w | Where-Object { ParseDbl($_.resultado_bruto) -gt 0 }
$l = $w | Where-Object { ParseDbl($_.resultado_bruto) -lt 0 }
$z = $w | Where-Object { ParseDbl($_.resultado_bruto) -eq 0 }
Write-Host ("gains=" + $g.Count + " losses=" + $l.Count + " zeros=" + $z.Count)
$gainPts = ($g | Measure-Object -Property resultado_bruto -Sum).Sum
$lossPts = ($l | Measure-Object -Property resultado_bruto -Sum).Sum
$netPts = ($w | Measure-Object -Property resultado_bruto -Sum).Sum
Write-Host ("gainPts=" + $gainPts + " lossPts=" + $lossPts + " netPts=" + $netPts)
Write-Host ("--- primeiras 15 linhas com resultado ---")
$w | Select-Object -First 15 timestamp,direcao,resultado_bruto | Format-Table -AutoSize -Wrap
Write-Host ("--- valores distintos de pts (amostra) ---")
$w | Select-Object -First 40 resultado_bruto | Format-Table -AutoSize -HideTableHeaders
