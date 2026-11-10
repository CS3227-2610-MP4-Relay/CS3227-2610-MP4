# MP4 presentation

Open [Relay-MP4.html](Relay-MP4.html) in Chrome or Edge. The speaker notes are in [speaker-notes.md](speaker-notes.md).

The deck has 31 slides for about 30 minutes, then 8 backup slides holding the remaining full prompts. The bar at the bottom of every slide shows who is speaking: blue for zheng-jj, purple for Whimsyturtle. Next to it are the CS3227 lecture concepts the slide uses.

| Slides | Speaker | Focus | Time |
| --- | --- | --- | --- |
| 1–4 | zheng-jj | Product and the Test Coordinator role | 6 min |
| 5–8 | Whimsyturtle | Beta Tester role; multi-agent workflow, SWE and CI/CD | 6 min |
| 9–19 | zheng-jj | Agent-setup and Hermes experiments | 9 min |
| 20–31 | Whimsyturtle | App-context experiments and conclusion | 9 min |

## Presenting

- Next: `→`, `Space` or `Page Down`. Back: `←` or `Page Up`. `Home` and `End` jump to the ends.
- `F` toggles full screen. Adding `#12` to the address opens slide 12.
- The deck is one self-contained file: it needs no network and no other files, so it can be downloaded or sent on its own. The app screenshots from [`../docs/images/`](../docs/images/) are embedded in it.
- GitHub shows an `.html` file as source. To see the slides, download the file and open it in a browser.

## Exporting to PDF

Press `Ctrl+P` and choose **Save as PDF**. The page size is already set to one slide per page. From a terminal:

```bash
chrome --headless --no-pdf-header-footer --print-to-pdf=Relay-MP4.pdf presentations/Relay-MP4.html
```

## Sources

Figures, prompts and sample records come from the [agent-setups](../experiments/agent-setups/README.md) and [app-context](../experiments/app-context/README.md) archives; the screenshots are the User Guide's.
