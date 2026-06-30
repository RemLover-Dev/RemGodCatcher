# Plan: Fix Gelbooru 401 Auth Error + Add Gelbooru Credentials to Options

## Problem
- Gelbooru API returns 401 Unauthorized because `GELBOORU_API_KEY` and `GELBOORU_USER_ID` are not configured in the UI
- The Options tab only has Rule34 credential fields

## Changes

### 1. Add Gelbooru credentials to Options tab
**File:** `web/index.html`
- Add input fields for `gelbooruApiKey` and `gelbooruUserId` in the Options tab (similar to Rule34 fields)

### 2. Load/save Gelbooru credentials
**File:** `web/script.js`
- Update `loadApiSettings()` to populate Gelbooru fields
- Update `saveApiSettings()` to save Gelbooru credentials

### 3. Add Gelbooru credential routes
**File:** `Rem_catcher.py`
- Update `/api/api-settings` GET to return Gelbooru credentials
- Update `/api/api-settings` POST to save Gelbooru credentials to `.env`

### 4. Better error handling in worker
**File:** `workers/gelbooru.py`
- Add clear log message when credentials are missing
- Don't send empty credentials (causes 401)

## Verification
1. Start the app, go to Options tab
2. Enter Gelbooru API key and User ID
3. Click Save
4. Test downloading from Gelbooru tab - should work without 401
