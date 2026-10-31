param(
    [string]$SvgPath = 'docs/figures/ternary_cell_schematic.svg',
    [string]$PngPath = 'docs/figures/ternary_cell_schematic.png',
    [int]$Scale = 2
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing

if ($Scale -lt 1 -or $Scale -gt 4) { throw 'Scale must be between 1 and 4.' }
$source = (Resolve-Path -LiteralPath $SvgPath).Path
$target = [IO.Path]::GetFullPath($PngPath)
[xml]$svg = Get-Content -LiteralPath $source -Raw -Encoding UTF8
$canvas = $svg.DocumentElement
$width = [int]$canvas.GetAttribute('width')
$height = [int]$canvas.GetAttribute('height')
$bitmap = [System.Drawing.Bitmap]::new($width * $Scale, $height * $Scale)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
$graphics.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit
$graphics.ScaleTransform($Scale, $Scale)

try {
    foreach ($element in $canvas.ChildNodes) {
        if ($element.NodeType -ne [System.Xml.XmlNodeType]::Element) { continue }
        switch ($element.LocalName) {
            'rect' {
                $x = [float]$element.GetAttribute('x')
                $y = [float]$element.GetAttribute('y')
                $w = [float]$element.GetAttribute('width')
                $h = [float]$element.GetAttribute('height')
                $fill = $element.GetAttribute('fill')
                if ($fill) {
                    $brush = [System.Drawing.SolidBrush]::new(
                        [System.Drawing.ColorTranslator]::FromHtml($fill))
                    try { $graphics.FillRectangle($brush, $x, $y, $w, $h) }
                    finally { $brush.Dispose() }
                }
                $stroke = $element.GetAttribute('stroke')
                if ($stroke) {
                    $weight = [float]$element.GetAttribute('stroke-width')
                    $pen = [System.Drawing.Pen]::new(
                        [System.Drawing.ColorTranslator]::FromHtml($stroke), $weight)
                    try { $graphics.DrawRectangle($pen, $x, $y, $w, $h) }
                    finally { $pen.Dispose() }
                }
            }
            'line' {
                $pen = [System.Drawing.Pen]::new(
                    [System.Drawing.ColorTranslator]::FromHtml($element.GetAttribute('stroke')),
                    [float]$element.GetAttribute('stroke-width'))
                $pen.StartCap = [System.Drawing.Drawing2D.LineCap]::Round
                $pen.EndCap = [System.Drawing.Drawing2D.LineCap]::Round
                try {
                    $graphics.DrawLine($pen,
                        [float]$element.GetAttribute('x1'), [float]$element.GetAttribute('y1'),
                        [float]$element.GetAttribute('x2'), [float]$element.GetAttribute('y2'))
                } finally { $pen.Dispose() }
            }
            'circle' {
                $cx = [float]$element.GetAttribute('cx')
                $cy = [float]$element.GetAttribute('cy')
                $radius = [float]$element.GetAttribute('r')
                $brush = [System.Drawing.SolidBrush]::new(
                    [System.Drawing.ColorTranslator]::FromHtml($element.GetAttribute('fill')))
                try {
                    $graphics.FillEllipse($brush, $cx - $radius, $cy - $radius,
                        2 * $radius, 2 * $radius)
                } finally { $brush.Dispose() }
            }
            'text' {
                $size = [float]$element.GetAttribute('font-size')
                $style = if ($element.GetAttribute('font-weight') -eq '700') {
                    [System.Drawing.FontStyle]::Bold
                } else { [System.Drawing.FontStyle]::Regular }
                $font = [System.Drawing.Font]::new('Arial', $size, $style,
                    [System.Drawing.GraphicsUnit]::Pixel)
                $brush = [System.Drawing.SolidBrush]::new(
                    [System.Drawing.ColorTranslator]::FromHtml($element.GetAttribute('fill')))
                try {
                    $value = $element.InnerText
                    $textWidth = $graphics.MeasureString($value, $font).Width
                    $x = [float]$element.GetAttribute('x')
                    $anchor = $element.GetAttribute('text-anchor')
                    if ($anchor -eq 'middle') { $x -= $textWidth / 2 }
                    if ($anchor -eq 'end') { $x -= $textWidth }
                    $y = [float]$element.GetAttribute('y') - $size * 0.85
                    $graphics.DrawString($value, $font, $brush, $x, $y)
                } finally { $font.Dispose(); $brush.Dispose() }
            }
        }
    }
    $directory = [IO.Path]::GetDirectoryName($target)
    [IO.Directory]::CreateDirectory($directory) | Out-Null
    $bitmap.Save($target, [System.Drawing.Imaging.ImageFormat]::Png)
    Write-Output $target
} finally {
    $graphics.Dispose()
    $bitmap.Dispose()
}
