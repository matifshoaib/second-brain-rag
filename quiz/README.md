# Second Brain Drill

Active recall over every note in the Second Brain. It writes a question from a note's own text with the local model, grades your free-text answer against key points taken from that same text, and schedules the note again with spaced repetition. Every drillable note enters rotation, spread across vaults, so over time it checks you on everything.

Runs beside the RAG app (port 8000) on **port 8010**. It only reads `chunks.jsonl`; it never touches Chroma, the vault or `app.py`. Your progress lives in `quiz/quiz.db` (git-ignored).

## Run

```bash
cd ~/brain/second-brain-rag
.venv/bin/python3 quiz/quiz_app.py
# open http://localhost:8010   (over Tailscale: http://<mac-tailscale-name>:8010)
```

## Run at login (launchd)

```bash
sed "s#__HOME__#$HOME#g" quiz/com.secondbrain.drill.plist > ~/Library/LaunchAgents/com.secondbrain.drill.plist
launchctl load ~/Library/LaunchAgents/com.secondbrain.drill.plist
# restart after code changes:
launchctl kickstart -k gui/$(id -u)/com.secondbrain.drill
# logs: quiz/drill.log
```

## How it decides what to ask

- **Queue:** reviews that are due come first, then new notes up to the daily limit (default 25, change it in Progress). New notes are pulled from the least-covered vault first.
- **Coverage:** 1,300+ drillable notes at 25/day is roughly two months to see everything once. Mastered = next review 21+ days out.
- **Question types rotate per note:** Explain → Apply → Compare → Spot the error, plus Elicit / Specify / Design / Regulatory when the note has a how-layer. The first question on any note is always Explain.
- **Long notes** are split into ~5,500-character windows; each review of that note uses a different window.
- **Skipped:** stubs under 600 characters and index / MOC / README / template notes.

## Grading

- The model marks each key point hit / partial / missed and lists factual errors. **The score is computed in code** (hit = 1, partial = 0.5, minus 12 per error up to 2), not taken from the model.
- Score → suggested grade: <40 Again (back in 10 min), <65 Hard, <85 Good, 85+ Easy. You can override with 1–4; the next interval is shown under each button.
- "I don't know" scores 0 and shows the model answer. "Bad question" throws the question away and writes a new one. "Later" pushes the note back 4 hours.

## Keys

`⌘/Ctrl + Enter` submit · `1`–`4` grade · `Enter` accept the suggested grade · `S` progress · `Esc` close

## After adding notes

Stamp → chunk → embed as usual, then press **Rescan** in Progress (or restart the drill). New notes join the new queue; deleted notes are retired.

## Settings (env, optional)

| Variable | Default | |
|---|---|---|
| `QUIZ_PORT` | 8010 | |
| `QUIZ_MODEL` | `GEN_MODEL` from `.env` (qwen3:8b) | any Ollama model |
| `QUIZ_DB` | `quiz/quiz.db` | |
| `QUIZ_PREFETCH` | 2 | questions prepared ahead in the background |
