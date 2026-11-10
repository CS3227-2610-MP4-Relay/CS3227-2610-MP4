# MP4 presentation

[Open the deck](Relay-MP4.pptx). Its 17 slides include speaker notes targeting 30 minutes: 15 minutes each for zheng-jj (blue) and Whimsyturtle (purple).

The deck is editable in PowerPoint. [`source/content.json`](source/content.json) holds the notes, timings and source references; [`source/build_deck.ps1`](source/build_deck.ps1) builds the layouts using installed Microsoft PowerPoint on Windows.

To rebuild from the repository root:

```powershell
.\presentations\source\build_deck.ps1 -OutputName Relay-MP4-rebuilt.pptx
```

The script refuses to overwrite an existing deck. Rendered previews and its check report go to the ignored `tmp/relay-mp4-presentation/` directory.
