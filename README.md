# SaveThatTune (personal, low-cost music capture tool)

This project gives you a simple phone-friendly web tool:

1. Enter **artist + title + optional show date**.
2. It searches in order with artist-aware branching:
   - **Phish** requests: **Spotify → phish.in → YouTube fallback**
   - **Any other artist**: **Spotify → Live Music Archive → YouTube fallback**
3. If matched:
   - Spotify: saves track to your Spotify library.
   - LMA/phish.in: downloads audio to your NAS folder and tags file as favorite.
   - YouTube fallback: extracts audio and saves MP3 to your NAS folder, then tags as favorite.
4. Logs every action to SQLite.
5. Emails you the result.

## Why this stack is beginner-friendly and cheap
- Free/open-source Python stack (FastAPI + SQLite).
- Runs on Mac or NAS Docker without paid cloud services.
- Only ongoing costs are services you already use (Spotify account, email provider).

## Quick setup (Mac with VS Code)

## 1) Install Python 3.11+
Use `brew install python` if needed.

## 2) Create environment and install deps
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 3) Configure secrets
```bash
cp .env.example .env
```
Edit `.env` values.

## 4) Run
```bash
set -a; source .env; set +a
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open `http://YOUR-MAC-IP:8000` on your phone browser.

## API usage
`POST /capture` requires `X-Api-Key` header.

Example:
```bash
curl -X POST http://localhost:8000/capture \
  -H 'Content-Type: application/json' \
  -H 'X-Api-Key: change-me-long-random-key' \
  -d '{"artist":"Grateful Dead","title":"Eyes of the World","show_date":"1974-06-18"}'
```

## Matching details
- Uses fuzzy token matching for artist/title to handle variant spellings.
- Spotify is always checked first.
- If artist is Phish, fallback is phish.in.
- For non-Phish artists, fallback is Live Music Archive.
- If the selected path has no confident match, a YouTube audio-extraction fallback is attempted.
- If you provide a show date, Spotify candidates get a score bonus when album metadata aligns with the date.
- Cross-reference date hints are artist-aware:
  - Grateful Dead/others use DeadDisc (`https://www.deaddisc.com/GDFD_Dead_By_Date.htm`)
  - Phish uses phish.net LivePhish charts (`https://phish.net/charts/livephish`)

## NAS notes
Set `SAVE_THAT_TUNE_NAS_ROOT` to your mounted Synology music folder.
Examples:
- Mac mount: `/Volumes/music/inbox`
- Synology local path in container: `/volume1/music/inbox`

## Log and status
- SQLite file default: `data/actions.db`
- Recent requests endpoint: `GET /actions` with API key header.

## Important limitations for MVP
- LMA/phish.in downloadable file resolution can vary by release; current implementation tries common MP3 URLs first.
- YouTube fallback requires `yt-dlp` and `ffmpeg` installed on the host.
- You should validate favorite tag behavior with your preferred music player/library.
- For production reliability, run this under a process manager (launchd, Docker restart policy, or Synology Container Manager).
