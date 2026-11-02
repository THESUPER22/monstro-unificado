$ci = [System.Globalization.CultureInfo]::InvariantCulture
Write-Host ("'-80.0' -gt 0 = " + ('-80.0' -gt 0))
Write-Host ("'-80.0' -lt 0 = " + ('-80.0' -lt 0))
Write-Host ("'80.0' -gt 0 = " + ('80.0' -gt 0))
Write-Host ("'0.0' -eq 0 = " + ('0.0' -eq 0))
Write-Host ("[double]'-80.0' = " + [double]::Parse('-80.0', [System.Globalization.NumberStyles]::Float, $ci))
Write-Host ("[double]'-80.0' -gt 0 = " + ([double]::Parse('-80.0', [System.Globalization.NumberStyles]::Float, $ci) -gt 0))

$d = Import-Csv C:\AIOFEN\logs\modelo_a_shadow.csv -Delimiter ','
$w = $d | Where-Object { [string]::IsNullOrWhiteSpace($_.resultado_bruto) -eq $false }
Write-Host ("--- teste filtro direto na string ---")
$g2 = $w | Where-Object { $_.resultado_bruto -gt 0 }
$l2 = $w | Where-Object { $_.resultado_bruto -lt 0 }
$z2 = $w | Where-Object { $_.resultado_bruto -eq 0 }
Write-Host ("direct: gains=" + $g2.Count + " losses=" + $l2.Count + " zeros=" + $z2.Count)
Write-Host ("--- amostra filtro direto (deveria pegar apenas positivos) ---")
$g2 | Select-Object -First 8 timestamp,resultado_bruto | Format-Table -AutoSize -Wrap
