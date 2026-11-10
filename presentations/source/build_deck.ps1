param([string]$OutputName = 'Relay-MP4.pptx', [string]$OutputPath = '')

$ErrorActionPreference = 'Stop'
$buildDir = $PSScriptRoot
$taskDir = Split-Path $buildDir -Parent
$repoRoot = Split-Path $taskDir -Parent
$outPath = if($OutputPath){[IO.Path]::GetFullPath($OutputPath)}else{Join-Path $taskDir $OutputName}
$qaDir = Join-Path $repoRoot 'tmp\relay-mp4-presentation'
$renderDir = Join-Path $qaDir ('renders\' + [IO.Path]::GetFileNameWithoutExtension($outPath))
if (Test-Path -LiteralPath $outPath) { throw 'Output already exists. Choose a new -OutputName.' }
$content = Get-Content -LiteralPath (Join-Path $buildDir 'content.json') -Raw -Encoding UTF8 | ConvertFrom-Json
New-Item -ItemType Directory -Path $renderDir -Force | Out-Null

function RGB([string]$Hex) {
    $v = $Hex.TrimStart('#')
    return [Convert]::ToInt32($v.Substring(0,2),16) + 256*[Convert]::ToInt32($v.Substring(2,2),16) + 65536*[Convert]::ToInt32($v.Substring(4,2),16)
}
$C = @{
    ink = '20262B'; muted = '626A73'; line = 'D9DDE1'; bg = 'FAFAF8'; white = 'FFFFFF'
    blue = '235CAD'; blueLight = 'EAF0FA'; purple = '784BB1'; purpleLight = 'F0EAF8'
    green = '167250'; greenLight = 'E8F4ED'; red = 'AC403A'; redLight = 'F9EAE8'
    amber = '906313'; amberLight = 'FBF2DD'; grey = 'EDF0F2'
}

function Text($s,[string]$value,[double]$x,[double]$y,[double]$w,[double]$h,[double]$size=22,[string]$color='20262B',[bool]$bold=$false,[int]$align=1,[string]$font='Calibri') {
    $sh = $s.Shapes.AddTextbox(1,$x,$y,$w,$h)
    $sh.Name = 'Text-' + $s.Shapes.Count
    $sh.TextFrame.MarginLeft = 0; $sh.TextFrame.MarginRight = 0
    $sh.TextFrame.MarginTop = 0; $sh.TextFrame.MarginBottom = 0
    $sh.TextFrame.WordWrap = -1; $sh.TextFrame.AutoSize = 0
    $sh.TextFrame.TextRange.Text = $value
    $sh.TextFrame.TextRange.Font.Name = $font
    $sh.TextFrame.TextRange.Font.Size = $size
    $sh.TextFrame.TextRange.Font.Bold = $(if ($bold) {-1} else {0})
    $sh.TextFrame.TextRange.Font.Color.RGB = RGB $color
    $sh.TextFrame.TextRange.ParagraphFormat.Alignment = $align
    $sh.TextFrame.TextRange.ParagraphFormat.SpaceAfter = 0
    $sh.TextFrame.TextRange.ParagraphFormat.SpaceBefore = 0
    $sh.Left=$x; $sh.Top=$y; $sh.Width=$w; $sh.Height=$h
    return $sh
}
function Rect($s,[double]$x,[double]$y,[double]$w,[double]$h,[string]$fill,[string]$line='') {
    $sh = $s.Shapes.AddShape(1,$x,$y,$w,$h)
    $sh.Fill.ForeColor.RGB = RGB $fill
    if ($line) {$sh.Line.ForeColor.RGB = RGB $line; $sh.Line.Weight=1} else {$sh.Line.Visible=0}
    return $sh
}
function Box($s,[string]$value,[double]$x,[double]$y,[double]$w,[double]$h,[string]$fill='EDF0F2',[string]$color='20262B',[double]$size=22,[bool]$bold=$false) {
    $sh = Rect $s $x $y $w $h $fill
    $sh.TextFrame.MarginLeft=12; $sh.TextFrame.MarginRight=12
    $sh.TextFrame.MarginTop=8; $sh.TextFrame.MarginBottom=8
    $sh.TextFrame.WordWrap=-1; $sh.TextFrame.AutoSize=0; $sh.TextFrame.VerticalAnchor=3
    $sh.TextFrame.TextRange.Text=$value
    $sh.TextFrame.TextRange.Font.Name='Calibri'; $sh.TextFrame.TextRange.Font.Size=$size
    $sh.TextFrame.TextRange.Font.Bold=$(if($bold){-1}else{0})
    $sh.TextFrame.TextRange.Font.Color.RGB=RGB $color
    $sh.TextFrame.TextRange.ParagraphFormat.Alignment=2
    $sh.TextFrame.TextRange.ParagraphFormat.SpaceAfter=0
    return $sh
}
function Line($s,[double]$x1,[double]$y1,[double]$x2,[double]$y2,[string]$color='B2BAC1',[bool]$arrow=$false,[double]$weight=1.5) {
    $ln=$s.Shapes.AddLine($x1,$y1,$x2,$y2)
    $ln.Line.ForeColor.RGB=RGB $color; $ln.Line.Weight=$weight
    if($arrow){$ln.Line.EndArrowheadStyle=3}
    return $ln
}
function Label($s,[string]$value,[double]$x,[double]$y,[double]$w=850,[double]$size=17,[string]$color='626A73') {
    return Text $s $value $x $y $w 40 $size $color
}
function Screenshot($s,[string]$name,[double]$cropX,[double]$cropY,[double]$cropW,[double]$cropH,[double]$x,[double]$y,[double]$w) {
    Add-Type -AssemblyName System.Drawing
    $path=Join-Path $repoRoot ('docs\images\'+$name)
    $image=[Drawing.Image]::FromFile($path)
    $pixelW=$image.Width; $pixelH=$image.Height; $image.Dispose()
    $picture=$s.Shapes.AddPicture($path,0,-1,0,0,-1,-1)
    $picture.LockAspectRatio=0
    $scale=$w/$cropW
    $crop=$picture.PictureFormat.Crop
    $crop.ShapeWidth=$w; $crop.ShapeHeight=$cropH*$scale
    $crop.PictureWidth=$pixelW*$scale; $crop.PictureHeight=$pixelH*$scale
    $crop.ShapeLeft=$x; $crop.ShapeTop=$y
    $crop.PictureOffsetX=($pixelW/2-$cropX-$cropW/2)*$scale
    $crop.PictureOffsetY=($pixelH/2-$cropY-$cropH/2)*$scale
    $picture.Name='Screenshot-'+$name
    $picture.AlternativeText='Actual Relay screen from docs/images/'+$name+'; surrounding page context retained.'
    return $picture
}
function Walkthrough($s,$labels,[string]$accent,[string]$fill) {
    $count=$labels.Count; $gap=28; $width=(864-($count-1)*$gap)/$count
    for($j=0;$j -lt $count;$j++){
        $x=48+$j*($width+$gap)
        $null=Box $s $labels[$j] $x 114 $width 34 $fill $accent 18 $true
        if($j -lt $count-1){$null=Line $s ($x+$width+5) 131 ($x+$width+$gap-5) 131 $C.muted $true}
    }
}
function ScreenView($s,[string]$name,[double]$cropX,[double]$cropY,[double]$cropW,[double]$cropH) {
    $scale=[Math]::Min(590/$cropW,350/$cropH)
    $x=48+(590-$cropW*$scale)/2
    $y=129+(350-$cropH*$scale)/2
    $null=Screenshot $s $name $cropX $cropY $cropW $cropH $x $y ($cropW*$scale)
    return [pscustomobject]@{x=$x;y=$y;right=$x+$cropW*$scale;scale=$scale;cropX=$cropX;cropY=$cropY}
}
function Highlight($s,$view,[double]$px,[double]$py,[double]$pw,[double]$ph,[string]$title,[string]$detail,[double]$labelY) {
    $x=$view.x+($px-$view.cropX)*$view.scale
    $y=$view.y+($py-$view.cropY)*$view.scale
    $w=$pw*$view.scale; $h=$ph*$view.scale
    $outline=Rect $s $x $y $w $h $C.white
    $outline.Fill.Visible=0; $outline.Line.Visible=-1
    $outline.Line.ForeColor.RGB=RGB 'D13636'; $outline.Line.Weight=2
    $outline.Name='Highlight-'+$title
    $center=$y+$h/2; $anchor=$labelY+20
    $bend=$view.right+16
    $null=Line $s ($x+$w) $center $bend $center 'D13636' $false 1
    $null=Line $s $bend $center 687 $anchor 'D13636' $false 1
    $null=Text $s $title 704 $labelY 208 54 22 $C.ink $true
    $null=Text $s $detail 704 ($labelY+57) 208 47 18 $C.muted
}
function RoleScreens($s,[int]$number) {
    switch($number){
        3 {
            $view=ScreenView $s 'draft-round.png' 160 60 960 760
            Highlight $s $view 208 239 862 56 'Draft state' 'Edit the round before publishing' 151
            Highlight $s $view 421 410 651 375 'Acceptance criteria' 'Define what the tests should cover' 333
        }
        4 {
            $view=ScreenView $s 'ai-suggestions.png' 160 60 960 1160
            Highlight $s $view 208 321 864 215 'Select criteria' 'Choose the source for drafting' 138
            Highlight $s $view 208 810 864 333 'Review the draft' 'Check steps, results and criterion links' 264
            Highlight $s $view 208 1155 166 46 'Use this draft' 'Review it in the normal form' 390
        }
        5 {
            $view=ScreenView $s 'record-result.png' 160 60 960 1100
            Highlight $s $view 208 555 864 395 'Outcome + observation' 'Record what happened' 138
            Highlight $s $view 208 966 211 44 'Save or submit' 'Keep a draft, then submit when ready' 264
            Highlight $s $view 208 1084 206 45 'Observation feedback' 'Review the report before submission' 390
        }
        6 {
            $view=ScreenView $s 'observation-feedback.png' 160 60 960 1340
            Highlight $s $view 208 341 864 105 'Saved observation' 'The original report stays visible' 138
            Highlight $s $view 208 1120 201 46 'Request feedback' 'AI runs after an explicit action' 264
            Highlight $s $view 208 1210 864 167 'Questions to consider' 'Decide what to edit yourself' 390
        }
    }
}
function NativeTable($s,$rows,[double]$x,[double]$y,[double]$w,[double]$h,$widths,[double]$size=21,[double]$padding=8) {
    $sh=$s.Shapes.AddTable($rows.Count,$rows[0].Count,$x,$y,$w,$h)
    $tb=$sh.Table
    for($col=1;$col -le $rows[0].Count;$col++) {$tb.Columns.Item($col).Width=[double]$widths[$col-1]}
    for($r=1;$r -le $rows.Count;$r++) {
        for($col=1;$col -le $rows[0].Count;$col++) {
            $cell=$tb.Cell($r,$col)
            $cell.Shape.Fill.ForeColor.RGB=RGB $(if($r -eq 1){$C.ink}else{$C.white})
            $tf=$cell.Shape.TextFrame
            $tf.MarginLeft=14; $tf.MarginRight=10; $tf.MarginTop=$padding; $tf.MarginBottom=$padding
            $tf.VerticalAnchor=3
            $tf.TextRange.Text=[string]$rows[$r-1][$col-1]
            $tf.TextRange.Font.Name='Calibri'; $tf.TextRange.Font.Size=$size
            $tf.TextRange.Font.Bold=$(if($r -eq 1 -or $col -eq 1){-1}else{0})
            $tf.TextRange.Font.Color.RGB=RGB $(if($r -eq 1){$C.white}else{$C.ink})
            $tf.TextRange.ParagraphFormat.SpaceAfter=0
            $tf.TextRange.ParagraphFormat.Alignment=$(if($col -eq 1){1}else{2})
            foreach($border in 1..4){$cell.Borders.Item($border).Visible=-1; $cell.Borders.Item($border).ForeColor.RGB=RGB $C.line; $cell.Borders.Item($border).Weight=0.5}
            foreach($border in 5..6){$cell.Borders.Item($border).Visible=0}
        }
    }
    return $sh
}
function CellColor($tb,[int]$r,[int]$col,[string]$fill,[string]$font) {
    $cell=$tb.Table.Cell($r,$col)
    $cell.Shape.Fill.ForeColor.RGB=RGB $fill
    $cell.Shape.TextFrame.TextRange.Font.Color.RGB=RGB $font
}
function ExperimentSlide($s,$item) {
    $accent=if($item.speaker -eq 'zheng-jj'){$C.blue}else{$C.purple}
    switch($item.layout) {
        'task_map' {
            $null=Label $s '135 counted runs. Claude Code, Codex and Hermes.' 48 114 864 21 $accent
            $null=NativeTable $s $item.rows 48 173 864 264 @(95,624,145) 21
        }
        'prompt' {
            $font=if($item.font){$item.font}else{'Calibri'}
            $null=Text $s $item.body 48 129 864 344 $item.size $C.ink $false 1 $font
        }
        'sample_run' {
            $null=NativeTable $s $item.rows 48 124 864 274 @(454,410) 20
            $null=Label $s 'Actual candidate line retained in the mutation fixture' 48 408 864 17 $accent
            $null=Text $s $item.code 48 440 864 29 18 $C.ink $false 1 'Consolas'
        }
        'setup_cost' {
            $null=Label $s 'Task 1 on Opus. Median cost and elapsed time.' 48 113 864 20
            $tb=NativeTable $s $item.rows 48 169 864 280 @(330,105,143,143,143) 20
            for($col=1;$col -le 5;$col++){CellColor $tb 2 $col $C.grey $C.ink}
            for($r=3;$r -le 7;$r++){foreach($col in 3..4){CellColor $tb $r $col $C.greenLight $C.green}}
        }
        'quality' {
            $steps=@('Hidden suite','Planted bugs','Blind review')
            for($j=0;$j -lt 3;$j++) {
                $x=48+304*$j
                $null=Box $s $steps[$j] $x 129 256 54 $C.blueLight $accent 23 $true
                if($j -lt 2){$null=Line $s ($x+268) 156 ($x+292) 156 $C.muted $true}
            }
            $tb=NativeTable $s $item.rows 48 220 864 208 @(430,434) 21
            CellColor $tb 2 2 $C.greenLight $C.green
            CellColor $tb 3 2 $C.greenLight $C.green
            CellColor $tb 4 2 $C.amberLight $C.amber
        }
        'hermes' {
            $null=Label $s 'Same model and tool. Compare within each task pair.' 48 113 864 20
            $tb=NativeTable $s $item.rows 48 168 864 282 @(256,105,118,143,120,122) 18
            foreach($col in 2..3){CellColor $tb 3 $col $C.greenLight $C.green; CellColor $tb 6 $col $C.redLight $C.red}
            foreach($col in 5..6){CellColor $tb 6 $col $C.greenLight $C.green}
            for($col=1;$col -le 6;$col++){CellColor $tb 4 $col $C.grey $C.muted}
        }
        'ideal' {
            $steps=@('One session builds','Consistency check','Independent review')
            for($j=0;$j -lt 3;$j++) {
                $x=48+304*$j
                $null=Box $s $steps[$j] $x 173 256 98 $(if($j -eq 1){$C.grey}else{$C.blueLight}) $C.ink 25 $true
                if($j -lt 2){$null=Line $s ($x+267) 222 ($x+292) 222 $C.muted $true}
            }
            $null=Text $s 'Requirements, decisions, tests and implementation' 247 312 530 63 24 $accent $true
            $null=Line $s 800 287 800 390 $C.muted
            $null=Line $s 800 390 176 390 $C.muted
            $null=Line $s 176 390 176 287 $C.muted $true
            $null=Label $s 'Limited repairs' 350 409 310 26 $accent
        }
        'v7_v8' {
            $null=Label $s 'V8 added four rules. Review findings did not consistently fall.' 48 113 864 20
            $tb=NativeTable $s $item.rows 48 177 864 256 @(510,177,177) 22
            for($r=2;$r -le 5;$r++){CellColor $tb $r 3 $C.redLight $C.red}
        }
        'dev_takeaways' {$null=NativeTable $s $item.rows 48 162 864 265 @(410,454) 22}
        'stages' {$null=NativeTable $s $item.rows 48 130 864 303 @(330,534) 21}
        'app_design' {
            $null=Text $s '12 scenarios' 48 137 864 50 36 $C.ink $true 2
            $null=Text $s '3 models × 3 conditions × 5 repeats' 48 204 864 50 30 $accent $true 2
            $null=Text $s '540 attempts' 48 272 864 60 44 $C.ink $true 2
            $labels=@('Relevant only','App clutter','Off-topic text')
            for($j=0;$j -lt 3;$j++){$null=Box $s $labels[$j] (48+300*$j) 370 264 60 $C.purpleLight $accent 22}
        }
        'sample_answer' {
            $null=Text $s $item.body 48 135 864 112 19 $C.ink $false 1 'Consolas'
            $tb=NativeTable $s $item.rows 48 258 864 201 @(600,264) 18 3
            for($r=2;$r -le 6;$r++){CellColor $tb $r 2 $C.greenLight $C.green}
        }
        'calibration' {
            $null=Box $s 'Parser: structure' 48 130 390 65 $C.grey $C.ink 25 $true
            $null=Line $s 449 163 502 163 $C.muted $true
            $null=Box $s 'Rubric: usefulness' 522 130 390 65 $C.purpleLight $accent 25 $true
            $null=NativeTable $s $item.rows 48 238 864 199 @(580,284) 22
        }
        'draft_results' {
            $null=Label $s 'All checks met, out of 30 attempts per cell' 48 113 864 21
            $tb=NativeTable $s $item.rows 48 170 864 218 @(294,190,190,190) 23
            for($r=2;$r -le 4;$r++){CellColor $tb $r 2 $C.grey $C.ink}
            foreach($r in 2..3){foreach($col in 3..4){CellColor $tb $r $col $C.redLight $C.red}}
            CellColor $tb 4 3 $C.grey $C.muted; CellColor $tb 4 4 $C.redLight $C.red
            $null=Text $s 'One clutter answer added tests about astronomy, textiles, gardening and audio.' 48 417 864 48 20 $C.ink
        }
        'feedback_results' {
            $null=Label $s 'All checks met, out of 30 attempts per cell' 48 113 864 21
            $tb=NativeTable $s $item.rows 48 170 864 218 @(294,190,190,190) 23
            for($r=2;$r -le 4;$r++){CellColor $tb $r 2 $C.grey $C.ink}
            foreach($col in 3..4){CellColor $tb 2 $col $C.grey $C.muted; CellColor $tb 3 $col $C.redLight $C.red}
            CellColor $tb 4 3 $C.greenLight $C.green; CellColor $tb 4 4 $C.grey $C.muted
            $null=Text $s 'Complete reports F3 and F4: 43/43 accepted answers each still asked unnecessary questions.' 48 417 864 48 20 $C.ink
        }
        'app_resources' {
            $null=Label $s 'Drafting: app clutter compared with relevant-only' 48 113 864 21
            $tb=NativeTable $s $item.rows 48 180 864 238 @(216,216,244,188) 21
            foreach($r in 2..3){CellColor $tb $r 2 $C.redLight $C.red}
            CellColor $tb 4 2 $C.grey $C.muted
            for($r=2;$r -le 4;$r++){CellColor $tb $r 3 $C.amberLight $C.amber}
            CellColor $tb 2 4 $C.redLight $C.red; CellColor $tb 3 4 $C.greenLight $C.green; CellColor $tb 4 4 $C.redLight $C.red
        }
        'next' {
            $steps=@('Human sample review','Narrow prompt change','Frozen comparison')
            for($j=0;$j -lt 3;$j++) {
                $x=48+304*$j
                $null=Box $s $steps[$j] $x 174 256 102 $C.purpleLight $accent 25 $true
                if($j -lt 2){$null=Line $s ($x+268) 225 ($x+292) 225 $C.muted $true}
            }
            $null=Text $s 'Empty answers, actual actions and background boundaries' 80 333 800 78 28 $C.ink $true 2
        }
        'close' {
            $null=Text $s 'In development' 48 153 395 42 24 $C.blue $true
            $null=Text $s "Focused building context`nIndependent review" 48 221 396 130 30 $C.ink $true
            $null=Text $s 'In the app' 522 153 390 42 24 $C.purple $true
            $null=Text $s "Relevant evidence`nHuman decisions" 522 221 390 130 32 $C.ink $true
            $null=Line $s 480 148 480 359 $C.line
            $null=Text $s 'Evaluate quality against the resources spent' 48 414 864 50 28 $C.ink $true 2
        }
        'record' {$null=NativeTable $s $item.rows 48 124 864 338 @(460,404) 17 2}
        default {throw ('Unknown layout: '+$item.layout)}
    }
    if($item.footer){$null=Text $s $item.footer 48 470 864 20 12.5 $C.muted}
}
function Base([int]$i) {
    $item=$content.slides[$i-1]
    $s=$script:deck.Slides.Add($i,12)
    $s.FollowMasterBackground=0; $s.Background.Fill.ForeColor.RGB=RGB $C.bg
    $accent=$(if($item.speaker -eq 'zheng-jj'){$C.blue}else{$C.purple})
    if($i -ne 1){$null=Text $s $item.title 48 35 866 78 32 $C.ink $true}
    $null=Line $s 48 494 912 494 $C.line $false 0.7
    $null=Rect $s 48 510 9 9 $accent
    $null=Text $s $item.speaker 66 505 400 22 12 $accent $true
    $mainCount=@($content.slides | Where-Object {-not $_.backup}).Count
    $page=if($item.backup){'Backup '+($i-$mainCount)}else{[string]$i+' / '+$mainCount}
    $null=Text $s $page 806 505 106 22 11 $C.muted $false 3
    $start=0; for($j=0;$j -lt $i-1;$j++){$start += $content.slides[$j].seconds}
    $end=$start+$item.seconds
    function Stamp([int]$v){return ('{0}:{1:00}' -f [math]::Floor($v/60),($v%60))}
    $timing=if($item.backup){'Backup: outside the 40-minute presentation'}else{'Target: '+(Stamp $item.seconds)+' | Running time: '+(Stamp $start)+'-'+(Stamp $end)}
    $note='Speaker: '+$item.speaker+"`r`n"+$timing+"`r`n`r`n"+$item.notes+"`r`n`r`nSources:`r`n"+($item.sources -join "`r`n")
    $s.NotesPage.Shapes.Placeholders.Item(2).TextFrame.TextRange.Text=$note
    return $s
}

$ppt=$null; $script:deck=$null
try {
    $ppt=New-Object -ComObject PowerPoint.Application
    $script:deck=$ppt.Presentations.Add(0)
    $deck.PageSetup.SlideWidth=960; $deck.PageSetup.SlideHeight=540

    # 1: cover
    $s=Base 1
    $null=Text $s 'Relay' 56 130 800 105 76 $C.ink $true
    $null=Text $s 'A beta-testing portal for small software teams' 60 247 810 54 27 $C.muted
    $null=Text $s 'CS3227 Mini Project 4' 60 342 800 35 20 $C.muted
    $null=Text $s 'zheng-jj' 60 405 200 34 20 $C.blue $true
    $null=Text $s 'Whimsyturtle' 270 405 240 34 20 $C.purple $true

    # 2: product loop
    $s=Base 2
    $null=Label $s 'From acceptance criteria to results on a specific build' 48 113 864 21
    $steps=@('Prepare','Publish','Test','Review','Retest')
    for($j=0;$j -lt 5;$j++) {
        $x=48+176*$j; $fill=$(if($j -eq 2){$C.purpleLight}else{$C.blueLight}); $color=$(if($j -eq 2){$C.purple}else{$C.blue})
        $null=Box $s $steps[$j] $x 218 148 76 $fill $color 23 $true
        if($j -lt 4){$null=Line $s ($x+153) 256 ($x+170) 256 $C.muted $true}
    }
    $null=Text $s 'Test Coordinator' 48 335 250 35 22 $C.blue $true
    $null=Text $s 'Draft tests from criteria' 48 378 350 40 21 $C.ink
    $null=Text $s 'Beta Tester' 535 335 300 35 22 $C.purple $true
    $null=Text $s 'Clarify observations' 535 378 350 40 21 $C.ink
    $null=Label $s 'AI supports each role. People review and save.' 48 449 864 18

    # 3-6: fuller app pages with editable red highlight boxes and labels
    $s=Base 3
    RoleScreens $s 3
    $s=Base 4
    RoleScreens $s 4
    Write-Output 'Created slides 1-4'
    $s=Base 5
    RoleScreens $s 5
    $s=Base 6
    RoleScreens $s 6

    # 7: multi-agent workflow
    $s=Base 7
    $null=Label $s 'Spec-Anchored Development' 48 112 864 19 $C.purple
    $null=Box $s 'Coordinator: scope, dispatch, checkpoints' 48 161 864 54 $C.purpleLight $C.purple 21 $true
    $null=Box $s "Spec + plan" 48 270 170 78 $C.grey $C.ink 23
    $null=Line $s 228 309 259 309 $C.muted $true
    $null=Box $s 'Builder' 272 270 170 78 $C.grey $C.ink 23
    $null=Line $s 452 309 483 309 $C.muted $true
    $null=Box $s "Fixed`ncandidate" 496 270 170 78 $C.grey $C.ink 23
    $null=Line $s 676 309 707 309 $C.muted $true
    $null=Box $s 'Verifier' 720 252 192 54 $C.purpleLight $C.purple 22 $true
    $null=Box $s 'Security review*' 720 326 192 54 $C.purpleLight $C.purple 18
    $null=Line $s 816 392 816 431 $C.muted
    $null=Line $s 816 431 357 431 $C.muted
    $null=Line $s 357 431 357 361 $C.muted $true
    $null=Text $s 'Findings and repairs' 458 406 248 28 17 $C.muted $false 2
    $null=Label $s '* Selected by risk. Humans decide merge and release.' 48 461 864 15

    # 8: context routing and handoff
    $s=Base 8
    $null=Text $s 'Retrieve relevant paths' 48 129 395 38 23 $C.purple $true
    $labels=@('AGENTS.md','Relevant specs','Slice plan','Code + tests')
    for($j=0;$j -lt 4;$j++) {
        $null=Box $s $labels[$j] 48 (185+62*$j) 340 45 $C.grey $C.ink 20
        if($j -lt 3){$null=Line $s 218 (234+62*$j) 218 (242+62*$j) $C.muted $true}
    }
    $null=Text $s 'Carry decisions forward' 500 129 410 38 23 $C.purple $true
    $null=Label $s 'Example: observation-feedback slice' 500 181 410 17
    $handoff=@('Candidate + relevant criteria','Actual checks','Findings + decisions','Next step')
    for($j=0;$j -lt 4;$j++){$null=Text $s $handoff[$j] 500 (234+42*$j) 412 35 21 $C.ink}
    $null=Label $s 'Risk-based roles     Focused checks     Tokens + elapsed + repairs' 48 450 864 18
    Write-Output 'Created slides 5-8'

    # Expanded experiments and complete sample evidence, followed by backups.
    for($number=9;$number -le $content.slides.Count;$number++) {
        $s=Base $number
        ExperimentSlide $s $content.slides[$number-1]
    }
    Write-Output 'Created expanded experiment slides; saving and rendering'
    $deck.SaveAs($outPath,24)
    foreach($slide in $deck.Slides){$slide.Export((Join-Path $renderDir ('slide-{0:00}.png' -f $slide.SlideIndex)),'PNG',1600,900)}

    $fitIssues=@()
    foreach($slide in $deck.Slides){
        foreach($shape in $slide.Shapes){
            if($shape.HasTextFrame -eq -1 -and $shape.TextFrame.HasText -eq -1){
                if($shape.TextFrame2.TextRange.BoundHeight -gt ($shape.Height+2)) {
                    $fitIssues += [pscustomobject]@{slide=$slide.SlideIndex;shape=$shape.Name;boundHeight=$shape.TextFrame2.TextRange.BoundHeight;height=$shape.Height}
                }
            }
        }
    }
    $speakerTotals=@{}; $total=0
    foreach($item in $content.slides){$total+=$item.seconds; $speakerTotals[$item.speaker]+=$item.seconds}
    $report=[pscustomobject]@{file=$outPath;slides=$deck.Slides.Count;seconds=$total;speakers=$speakerTotals;textFitIssues=$fitIssues;renders=$renderDir}
    $report | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $qaDir 'build-report.json') -Encoding UTF8
    $report | ConvertTo-Json -Depth 5 | Write-Output
    $deck.Close(); $script:deck=$null
    $ppt.Quit(); $ppt=$null
} finally {
    if($script:deck){try{$script:deck.Close()}catch{}}
    if($ppt){try{$ppt.Quit()}catch{}}
    [GC]::Collect(); [GC]::WaitForPendingFinalizers()
}
