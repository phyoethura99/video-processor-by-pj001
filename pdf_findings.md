# PDF Findings from `saimyanmarpro_code.pdf`

## Source
- File: `/home/ubuntu/upload/saimyanmarpro_code.pdf`
- Pages visually reviewed: 1-10

## Key findings observed so far

The PDF appears to contain a Streamlit-based or Streamlit-wrapped TTS interface plus embedded HTML/CSS/JS UI code.

### Python / backend related observations
- `main.py` imports include `streamlit`, `streamlit.components.v1`, `os`, `base64`, `uuid`, `sys`, `json`, `threading`, `edge_tts`, `asyncio`, and `mutagen.mp3`.
- A global semaphore is defined with max concurrency 10 via `threading.Semaphore(10)`.
- There is an admin/dashboard style stats counter using `website_stats.json`.

### Front-end / UI related observations
- There are sections with IDs such as:
  - `voices-grid`
  - `recap-grid`
  - `emotions-grid`
- The UI includes controls for:
  - speed slider (`speed`, min `-100`, max `100`)
  - pitch slider (`pitch`, min `-100`, max `100`)
  - text area input
  - audio preview / download
  - SRT download
- The PDF strongly suggests that the system supports selectable voices/models and selectable emotions/moods.

### TTS engine clue
- The clearly visible TTS backend import is `edge_tts`.
- This suggests the PDF likely uses Microsoft Edge / Azure-style neural voices exposed through the `edge-tts` Python package.

## Still needed
- Exact list of engines, models/voices, and moods/emotions.
- Exact mapping logic between selected model and selected mood.
- Any sample code for generating audio or subtitles.

## Reliability note
These findings are based on visual review of pages 1-10 only and should be verified by text extraction from the PDF source.
