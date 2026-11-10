param([string]$OutputName = 'Relay-MP4.pptx')

$ErrorActionPreference = 'Stop'
$buildDir = $PSScriptRoot
$taskDir = Split-Path $buildDir -Parent
$repoRoot = Split-Path $taskDir -Parent
$outPath = Join-Path $taskDir $OutputName
$qaDir = Join-Path $repoRoot 'tmp\relay-mp4-presentation'
$renderDir = Join-Path $qaDir ('renders\' + [IO.Path]::GetFileNameWithoutExtension($OutputName))
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
function NativeTable($s,$rows,[double]$x,[double]$y,[double]$w,[double]$h,$widths,[double]$size=21) {
    $sh=$s.Shapes.AddTable($rows.Count,$rows[0].Count,$x,$y,$w,$h)
    $tb=$sh.Table
    for($col=1;$col -le $rows[0].Count;$col++) {$tb.Columns.Item($col).Width=[double]$widths[$col-1]}
    for($r=1;$r -le $rows.Count;$r++) {
        for($col=1;$col -le $rows[0].Count;$col++) {
            $cell=$tb.Cell($r,$col)
            $cell.Shape.Fill.ForeColor.RGB=RGB $(if($r -eq 1){$C.ink}else{$C.white})
            $tf=$cell.Shape.TextFrame
            $tf.MarginLeft=14; $tf.MarginRight=10; $tf.MarginTop=8; $tf.MarginBottom=8
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
function Base([int]$i) {
    $item=$content.slides[$i-1]
    $s=$script:deck.Slides.Add($i,12)
    $s.FollowMasterBackground=0; $s.Background.Fill.ForeColor.RGB=RGB $C.bg
    $accent=$(if($item.speaker -eq 'zheng-jj'){$C.blue}else{$C.purple})
    if($i -ne 1){$null=Text $s $item.title 48 35 866 78 32 $C.ink $true}
    $null=Line $s 48 494 912 494 $C.line $false 0.7
    $null=Rect $s 48 510 9 9 $accent
    $null=Text $s $item.speaker 66 505 400 22 12 $accent $true
    $null=Text $s ([string]$i + ' / ' + $content.slides.Count) 842 505 70 22 11 $C.muted $false 3
    $start=0; for($j=0;$j -lt $i-1;$j++){$start += $content.slides[$j].seconds}
    $end=$start+$item.seconds
    function Stamp([int]$v){return ('{0}:{1:00}' -f [math]::Floor($v/60),($v%60))}
    $note='Speaker: '+$item.speaker+"`r`n"+'Target: '+(Stamp $item.seconds)+' | Running time: '+(Stamp $start)+'-'+(Stamp $end)+"`r`n`r`n"+$item.notes+"`r`n`r`nSources:`r`n"+($item.sources -join "`r`n")
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

    # 3: coordinator state diagram
    $s=Base 3
    $null=Box $s 'Draft' 48 153 240 70 $C.blueLight $C.blue 26 $true
    $null=Box $s 'Open' 360 153 240 70 $C.blueLight $C.blue 26 $true
    $null=Box $s 'Closed' 672 153 240 70 $C.grey $C.muted 26 $true
    $null=Line $s 301 188 345 188 $C.muted $true
    $null=Line $s 613 188 657 188 $C.muted $true
    $null=Text $s "Criteria + cases" 48 246 240 45 22 $C.ink $false 2
    $null=Text $s "Results + retests" 360 246 240 45 22 $C.ink $false 2
    $null=Text $s 'Read-only' 672 246 240 45 22 $C.ink $false 2
    $null=Label $s 'Each result keeps its build context' 48 332 864 20
    $null=Box $s "Build 1.4.0`nFail" 48 382 300 80 $C.redLight $C.red 23
    $null=Line $s 365 422 590 422 $C.muted $true
    $null=Text $s 'Retest selected cases' 372 371 218 35 16 $C.muted $false 2
    $null=Box $s "Build 1.4.1`nPass" 612 382 300 80 $C.greenLight $C.green 23

    # 4: drafting boundary
    $s=Base 4
    $null=Label $s 'Selected criteria' 48 130 395 20 $C.blue
    $null=Text $s 'A task title allows 1 to 80 characters.' 48 174 370 105 26 $C.ink $true
    $null=Line $s 429 220 490 220 $C.muted $true
    $null=Label $s 'Example draft' 520 130 392 20 $C.blue
    $null=Text $s "Enter an 81-character title.`n`nExpect an error and no added task." 520 174 385 142 24 $C.ink
    $null=Box $s 'AI suggestion' 48 365 230 72 $C.grey $C.ink 22
    $null=Line $s 291 401 340 401 $C.muted $true
    $null=Box $s 'Human review' 360 365 230 72 $C.blueLight $C.blue 22 $true
    $null=Line $s 603 401 652 401 $C.muted $true
    $null=Box $s 'Add test case' 672 365 240 72 $C.blueLight $C.blue 22 $true
    Write-Output 'Created slides 1-4'

    # 5: tester flow
    $s=Base 5
    $titles=@('Read case','Try the build','Save draft','Submit')
    for($j=0;$j -lt 4;$j++) {
        $x=48+224*$j
        $null=Box $s $titles[$j] $x 160 192 74 $C.purpleLight $C.purple 22 $true
        if($j -lt 3){$null=Line $s ($x+198) 197 ($x+217) 197 $C.muted $true}
    }
    $null=Text $s 'Observation' 48 287 400 35 20 $C.purple $true
    $null=Text $s '“The task was added, but it appeared at the bottom of the list.”' 48 335 840 82 30 $C.ink
    $null=Label $s 'Own drafts stay private. Earlier builds stay in history.' 48 450 864 19

    # 6: app AI boundary
    $s=Base 6
    $null=Box $s "Saved observation`nCase + linked criteria" 48 150 270 110 $C.purpleLight $C.purple 22
    $null=Line $s 332 205 375 205 $C.muted $true
    $null=Box $s 'SoC LLM' 395 150 170 110 $C.grey $C.ink 25 $true
    $null=Line $s 580 205 623 205 $C.muted $true
    $null=Box $s "Questions`nTester edits + submits" 643 150 269 110 $C.purpleLight $C.purple 22
    $null=Label $s 'Selected source' 48 284 270 18
    $null=Label $s 'Strict JSON' 395 284 200 18
    $null=Label $s 'Human oversight' 643 284 269 18
    $null=Line $s 48 357 912 357 $C.line
    $null=Text $s 'Quotas' 48 393 250 42 24 $C.ink $true
    $null=Text $s 'Deadline' 357 393 250 42 24 $C.ink $true
    $null=Text $s 'Manual fallback' 666 393 250 42 24 $C.ink $true

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

    # 9: development setup and actual prompt/output
    $s=Base 9
    $null=Label $s '14 setups across four Relay tasks' 48 112 864 23 $C.blue
    $null=Box $s 'Same task' 48 171 230 58 $C.grey $C.ink 22
    $null=Line $s 292 200 339 200 $C.muted $true
    $null=Box $s 'Changed setup' 360 171 230 58 $C.blueLight $C.blue 22 $true
    $null=Line $s 604 200 651 200 $C.muted $true
    $null=Box $s 'Tests + review' 672 171 240 58 $C.grey $C.ink 22
    $null=Label $s 'Task 1 prompt excerpt' 48 271 392 18 $C.blue
    $null=Text $s '“Refuse only the text-direction embedding, override and isolate characters: U+202A to U+202E and U+2066 to U+2069.”' 48 314 392 145 21 $C.ink
    $null=Label $s 'Actual candidate code, r1-mp4' 500 271 412 18 $C.blue
    $null=Rect $s 500 316 412 102 $C.grey
    $null=Text $s "if any(ord(char) in`n       BIDI_CONTROLS`n       for char in text):" 516 332 383 80 18 $C.ink $false 1 'Consolas'
    $null=Label $s 'Retained in the mutation fixture' 500 436 412 15

    # 10: native results table
    $s=Base 10
    $null=Label $s 'Task 1 on Opus. Median cost and elapsed time.' 48 112 864 20
    $rows=@(
        @('Setup','Cost, US$','Time, min'),
        @('MP4 baseline','8.97','30'),
        @('MP3 six roles','5.77','22'),
        @('Solo','3.35','13'),
        @('superpowers','4.14','12')
    )
    $tb=NativeTable $s $rows 48 180 864 250 @(430,217,217) 22
    for($r=3;$r -le 5;$r++){for($col=2;$col -le 3;$col++){CellColor $tb $r $col $C.greenLight $C.green}}
    for($col=1;$col -le 3;$col++){CellColor $tb 2 $col $C.grey $C.ink}
    $null=Label $s 'Green: lower than MP4. All passed full verification. API list prices.' 48 454 864 16

    # 11: quality and mutation
    $s=Base 11
    $rows=@(
        @('Measure','Observed result'),
        @('Hidden tests','Every counted run passed'),
        @('Planted bugs','Almost all caught all five'),
        @('Independent review','58 Medium+ findings, including 5 High')
    )
    $tb=NativeTable $s $rows 48 137 864 213 @(275,589) 22
    CellColor $tb 2 2 $C.greenLight $C.green; CellColor $tb 3 2 $C.greenLight $C.green
    CellColor $tb 4 2 $C.amberLight $C.amber
    $null=Label $s 'Original candidate' 48 374 390 17
    $null=Label $s 'Deliberately broken variant' 580 374 332 17
    $null=Text $s 'if any(...):' 48 418 330 44 25 $C.ink $false 1 'Consolas'
    $null=Line $s 421 434 546 434 $C.muted $true
    $null=Text $s 'if False:' 580 418 332 44 25 $C.red $false 1 'Consolas'

    # 12: experimental recommendation
    $s=Base 12
    $null=Label $s 'Experimental recommendation: ideal v7' 48 112 864 22 $C.blue
    $null=Box $s "One building`nsession" 48 206 248 104 $C.blueLight $C.blue 25 $true
    $null=Line $s 309 258 342 258 $C.muted $true
    $null=Box $s "Consistency`ncheck" 356 206 248 104 $C.grey $C.ink 25
    $null=Line $s 617 258 650 258 $C.muted $true
    $null=Box $s "Independent`nreview" 664 206 248 104 $C.blueLight $C.blue 25 $true
    $null=Label $s 'Requirements     Decisions     Tests     Code' 269 343 643 18
    $null=Text $s 'Extra process needs evidence of value' 48 411 864 52 28 $C.ink $true
    Write-Output 'Created slides 9-12'

    # 13: app experiment design
    $s=Base 13
    $null=Text $s '12 scenarios' 48 147 864 50 37 $C.ink $true 2
    $null=Text $s '3 models × 3 conditions × 5 repeats' 48 216 864 50 31 $C.purple $true 2
    $null=Text $s '540 attempts' 48 288 864 60 44 $C.ink $true 2
    $null=Box $s 'Relevant only' 48 397 264 60 $C.grey $C.ink 21
    $null=Box $s 'App clutter' 348 397 264 60 $C.purpleLight $C.purple 21
    $null=Box $s 'Off-topic text' 648 397 264 60 $C.purpleLight $C.purple 21
    $null=Label $s 'Six drafting + six feedback scenarios. Same production prompts and parsers.' 48 466 864 14

    # 14: app prompt and constructed output
    $s=Base 14
    $null=Label $s 'Production prompt excerpt' 48 113 864 17 $C.purple
    $null=Text $s '“If no useful detail is missing, return no questions.”' 48 152 864 50 26 $C.ink $true
    $null=Line $s 48 219 912 219 $C.line
    $null=Label $s 'Synthetic F2 input, shortened' 48 242 395 18 $C.purple
    $null=Text $s "Case: Apply Available, then export CSV.`n`nReport: Opened Items and exported. An Unavailable row appeared." 48 286 383 154 22 $C.ink
    $null=Line $s 443 345 484 345 $C.muted $true
    $null=Label $s 'Constructed calibration answer' 508 242 404 18 $C.purple
    $sampleAnswer = "{`"questions`": [`n  `"At the moment Export CSV was selected, what filter selection did Items show?`"`n]}"
    $null=Text $s $sampleAnswer 508 289 404 142 19 $C.ink $false 1 'Consolas'
    $null=Label $s 'Input summarized from F2. Answer quoted from cal-19.' 48 459 864 15

    # 15: all-check quality tables, native and editable
    $s=Base 15
    $null=Label $s 'All checks met, out of 30 attempts per cell' 48 112 864 21
    $null=Text $s 'Drafting' 48 165 390 35 23 $C.ink $true
    $null=Text $s 'Feedback' 494 165 418 35 23 $C.ink $true
    $d=@(@('Model','Relevant','Clutter','Off-topic'),@('Llama 8B','12','2','0'),@('Qwen 35B','29','20','25'),@('x-test-2','30','30','29'))
    $f=@(@('Model','Relevant','Clutter','Off-topic'),@('Llama 8B','0','0','0'),@('Qwen 35B','9','2','5'),@('x-test-2','5','9','5'))
    $dt=NativeTable $s $d 48 212 418 207 @(130,96,96,96) 17
    $ft=NativeTable $s $f 494 212 418 207 @(130,96,96,96) 17
    foreach($t in @($dt,$ft)){for($r=2;$r -le 4;$r++){CellColor $t $r 2 $C.grey $C.ink}}
    for($r=2;$r -le 3;$r++){for($col=3;$col -le 4;$col++){CellColor $dt $r $col $C.redLight $C.red}}
    CellColor $dt 4 3 $C.grey $C.muted; CellColor $dt 4 4 $C.redLight $C.red
    for($col=3;$col -le 4;$col++){CellColor $ft 2 $col $C.grey $C.muted; CellColor $ft 3 $col $C.redLight $C.red}
    CellColor $ft 4 3 $C.greenLight $C.green; CellColor $ft 4 4 $C.grey $C.muted
    $null=Label $s 'Against relevant-only: red lower, green higher, grey unchanged. Model-assessed quality.' 48 447 864 15

    # 16: resource deltas native table
    $s=Base 16
    $null=Label $s 'Drafting: app clutter compared with relevant-only' 48 112 864 21
    $rows=@(
        @('Model','Success change','Input tokens / call','Mean latency'),
        @('Llama 8B','−33.3 pp','+582','+5.66 s'),
        @('Qwen 35B','−30.0 pp','+580','−0.30 s'),
        @('x-test-2','0.0 pp','+574','+0.08 s')
    )
    $tb=NativeTable $s $rows 48 181 864 230 @(216,216,244,188) 21
    CellColor $tb 2 2 $C.redLight $C.red; CellColor $tb 3 2 $C.redLight $C.red; CellColor $tb 4 2 $C.grey $C.muted
    for($r=2;$r -le 4;$r++){CellColor $tb $r 3 $C.amberLight $C.amber}
    CellColor $tb 2 4 $C.redLight $C.red; CellColor $tb 3 4 $C.greenLight $C.green; CellColor $tb 4 4 $C.redLight $C.red
    $null=Label $s 'pp = percentage points. Paired scenario averages; measured token counters.' 48 444 864 16

    # 17: concise close
    $s=Base 17
    $null=Text $s 'In development' 48 153 395 42 24 $C.blue $true
    $null=Text $s "Fewer handoffs`nIndependent review" 48 221 396 130 32 $C.ink $true
    $null=Text $s 'In the app' 522 153 390 42 24 $C.purple $true
    $null=Text $s "Relevant context`nHuman decisions" 522 221 390 130 32 $C.ink $true
    $null=Line $s 480 148 480 359 $C.line
    $null=Text $s 'Evaluate quality against the resources spent' 48 414 864 50 28 $C.ink $true 2

    Write-Output 'Created slides 13-17; saving and rendering'
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
