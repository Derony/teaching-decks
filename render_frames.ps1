# 逐效果畫格渲染：依 anim.json 控制顯隱，每個動畫效果輸出一張畫格
$ErrorActionPreference = "Stop"
$root = "G:\我的雲端硬碟\teaching-decks"
$src = "$root\input\P1_培正地圖_不插電編程.pptx"
$animJson = "$root\extracted\P1_培正地圖_不插電編程\anim.json"
$outDir = "$root\extracted\P1_培正地圖_不插電編程\frames"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

# 用副本開啟（會動到顯隱/字色，絕不存檔）
$tmp = "$env:TEMP\p1_frames_copy.pptx"
Copy-Item $src $tmp -Force
$anim = Get-Content $animJson -Raw -Encoding UTF8 | ConvertFrom-Json

$pp = New-Object -ComObject PowerPoint.Application
$pres = $pp.Presentations.Open($tmp, $false, $false, $false)

# 形狀對照表 dump（驗證 XML spid == COM Shape.Id）
$mapLog = @()
foreach ($s in $pres.Slides) {
    foreach ($sh in $s.Shapes) {
        $mapLog += ("slide{0} id={1} name={2}" -f $s.SlideIndex, $sh.Id, $sh.Name)
    }
}
$mapLog | Set-Content "$outDir\_shapemap.txt" -Encoding utf8

function Get-ShapeById($slide, $id) {
    foreach ($sh in $slide.Shapes) { if ($sh.Id -eq [int]$id) { return $sh } }
    return $null
}

$W = 1280; $H = 720
foreach ($sl in $anim) {
    $slide = $pres.Slides.Item($sl.slide)
    $steps = $sl.steps
    if (-not $steps -or $steps.Count -eq 0) {
        # 無動畫頁：單張畫格
        $slide.Export("$outDir\slide$($sl.slide)_e000.png", "PNG", $W, $H)
        Write-Output ("slide {0}: 1 frame (static)" -f $sl.slide)
        continue
    }
    # 展平：效果序列（依步驟順序）
    $effects = @()
    foreach ($step in $steps) { foreach ($e in $step) { $effects += $e } }

    # 蒐集段落動畫的文字框 → run 級原色備份 + 全白遮蔽
    $paraShapes = @{}
    foreach ($e in $effects) {
        if ($e.PSObject.Properties.Name -contains 'para' -and $e.para) {
            $paraShapes[[string]$e.spid] = $true
        }
    }
    $runColors = @{}
    foreach ($sid in $paraShapes.Keys) {
        $sh = Get-ShapeById $slide $sid
        if ($null -eq $sh) { Write-Output "!! slide$($sl.slide) 找不到段落形狀 id=$sid"; continue }
        $tr = $sh.TextFrame.TextRange
        $pc = $tr.Paragraphs().Count
        for ($p = 1; $p -le $pc; $p++) {
            $par = $tr.Paragraphs($p)
            $rc = $par.Runs().Count
            for ($r = 1; $r -le $rc; $r++) {
                $runColors["$sid|$p|$r"] = $par.Runs($r).Font.Color.RGB
                $par.Runs($r).Font.Color.RGB = 16777215  # 白
            }
        }
    }
    # 整形狀動畫（非段落、非路徑）→ 先全部隱藏；路徑形狀 → 永久隱藏（前端覆疊）
    foreach ($e in $effects) {
        if ($e.PSObject.Properties.Name -contains 'para' -and $e.para) { continue }
        $sh = Get-ShapeById $slide $e.spid
        if ($null -eq $sh) { Write-Output "!! slide$($sl.slide) 找不到形狀 id=$($e.spid) ($($e.name))"; continue }
        $sh.Visible = 0  # msoFalse
    }

    # 基底畫格
    $slide.Export(("$outDir\slide{0}_e{1:d3}.png" -f $sl.slide, 0), "PNG", $W, $H)

    # 逐效果揭示
    $k = 0
    foreach ($e in $effects) {
        $k++
        $isPath = ($e.cls -eq 'path')
        if ($isPath) {
            # 路徑動畫：畫格保持隱藏（前端用原圖飛行），輸出與上一格相同的畫格佔位
            $slide.Export(("$outDir\slide{0}_e{1:d3}.png" -f $sl.slide, $k), "PNG", $W, $H)
            continue
        }
        if ($e.PSObject.Properties.Name -contains 'para' -and $e.para) {
            $sid = [string]$e.spid
            $sh = Get-ShapeById $slide $sid
            $tr = $sh.TextFrame.TextRange
            # para 是 0-based 起訖（含），COM 1-based
            for ($p = $e.para[0] + 1; $p -le $e.para[1] + 1; $p++) {
                $rc = $tr.Paragraphs($p).Runs().Count
                for ($r = 1; $r -le $rc; $r++) {
                    $key = "$sid|$p|$r"
                    if ($runColors.ContainsKey($key)) {
                        $tr.Paragraphs($p).Runs($r).Font.Color.RGB = $runColors[$key]
                    }
                }
            }
        } else {
            $sh = Get-ShapeById $slide $e.spid
            if ($null -ne $sh) { $sh.Visible = -1 }  # msoTrue
        }
        $slide.Export(("$outDir\slide{0}_e{1:d3}.png" -f $sl.slide, $k), "PNG", $W, $H)
    }
    Write-Output ("slide {0}: {1} frames" -f $sl.slide, ($k + 1))
}

$pres.Close()
$pp.Quit()
Write-Output "DONE -> $outDir"
