# MP4 presentation

[Open the deck](Relay-MP4.pptx). Its 31 presentation slides include speaker notes targeting 40 minutes: 20 minutes each for zheng-jj (blue) and Whimsyturtle (purple). Three backup slides sit outside that timing.

| Slides | Speaker | Focus | Time |
| --- | --- | --- | --- |
| 1–4 | zheng-jj | Product and Test Coordinator | 8 min |
| 5–8 | Whimsyturtle | Beta Tester and development workflow | 8 min |
| 9–19 | zheng-jj | Agent setups, Hermes, quality and ideal v7/v8 | 12 min |
| 20–31 | Whimsyturtle | App-context experiments, calibration, results and closing | 12 min |
| 32–34 | zheng-jj | Complete retained Hermes evaluator record | Backup |

Slides 3–6 show fuller views of the actual app screenshots in [`docs/images/`](../docs/images/), with editable red boxes and labels highlighting the relevant controls.

The experiment sections show the complete retained task message and complete frozen feedback system/user messages. The sample Hermes result includes every retained CSV field in the backup slides. Raw live replies were not retained in the experiment archives; the complete app sample answer is explicitly labelled as a constructed calibration answer.

The deck is editable in PowerPoint. [`source/content.json`](source/content.json) holds the notes, timings and source references; [`source/build_deck.ps1`](source/build_deck.ps1) builds the layouts using installed Microsoft PowerPoint on Windows.

To rebuild from the repository root:

```powershell
.\presentations\source\build_deck.ps1 -OutputName Relay-MP4-rebuilt.pptx
```

The script refuses to overwrite an existing deck. Rendered previews and its check report go to the ignored `tmp/relay-mp4-presentation/` directory.
