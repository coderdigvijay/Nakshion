# Gemini API Gotchas

## Model names
- `text-embedding-004` does NOT exist — use `models/gemini-embedding-001`
- `gemini-1.5-flash` removed from API — use `gemini-2.5-flash`
- `gemini-2.0-flash` may have zero quota on some projects

## system_instruction placement
- WRONG: `model.generate_content(contents, system_instruction=prompt)` — TypeError
- RIGHT: `genai.GenerativeModel("gemini-2.5-flash", system_instruction=prompt)` — pass at model creation

## API key source matters
- Keys from Google Cloud Console do NOT auto-enable free tier (limit: 0)
- Keys from aistudio.google.com auto-enable free tier (15 RPM)
- Always create keys via AI Studio → "Create API key in new project"

## Embedding rate limits
- Free tier: 100 requests/minute for embeddings
- 539 chunks = impossible to batch index via API
- **Solution:** Use local sentence-transformers instead of Gemini for embeddings

## Deprecated library warning
- `google-generativeai` package is deprecated, successor is `google.genai`
- The old package still works, warning is non-blocking
