# MusicSync

### Synchronize your Apple Music library with Spotify.
This tool matches songs between platforms with precision and gives you **full control over your data**.

# Features

- Syncs only playlists
   - To sync your entire library, add it to a single playlist
- 100% local processing – no third-party servers involved.
- Incremental syncing: tracks previously synced songs.
- Detailed logging of sync results, including match scores.
- Handles edge cases like artist collaborations (`feat.`, `&`, etc.)

<details>
<summary>🔍 Example Sync Report</summary>

| Apple Song Name   | Apple Artist     | Apple Album            | Spotify Song Name   | Spotify Artist   | Spotify Album   | Spotify Track ID       | Total Similarity | Song Similarity | Artist Similarity | Album Similarity |
|:------------------|:-----------------|:-----------------------|:--------------------|:-----------------|:----------------|:-----------------------|-----------------:|----------------:|------------------:|-----------------:|
| Caruso            | Fiorella Mannoia | A te (Special Edition) | Caruso              | Fiorella Mannoia | A te            | 2kWftUZ8PxLQtRvrHX3cIe |             0.79 |             1.0 |               1.0 |              0.30 |

</details>

# Installation

## 1. Register a Spotify Developer App

These steps have been validated with the website's version as of 2021-01-17.

1. Visit [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/) and create/log into your account
2. Click on `CREATE AN APP`
   - Provide the app name & description of your choice, tick the terms of service and click "CREATE"
3. In `EDIT SETTINGS`, under `Redirect URIs` add the following URLs:
   - `http://localhost:9000/callback/`
   - `http://localhost:8090`
4. Save your **Client ID** and **Client Secret** – you'll need them in Section 2.3.

## 2. Set-up Environment

### 2.1 Clone Repository

```commandline
git clone git@github.com:calyptis/MusicSync.git
cd MusicSync
```

### 2.2 Install Dependencies

Requires Python 3.12 or newer and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
```

This creates a virtual environment and installs the package in editable mode
together with its dependencies and the `dev` group (linting and testing tools).
Use `uv sync --no-dev` for a runtime-only install.

### 2.3 Add Your Credentials

Create a `.env` file in the project root:

```bash
cat > .env <<'EOF'
SPOTIFY_CLIENT_ID=your-client-id
SPOTIFY_CLIENT_SECRET=your-client-secret
SPOTIFY_REDIRECT_URI=http://localhost:9000/callback/
EOF
```

Replace the client ID and secret with the values obtained from step 4 in Section 1.
`.env` is git-ignored. Any of these may also be supplied as ordinary environment
variables, which take precedence over the file.


# Syncing Your Library

## Step 1: Export from Apple Music

- Open the Apple Music app (tested with version 1.2.5.7)
- Go to File → Library → Export Library...
- Save the file as `Library.xml` in the `data/apple_music/` directory

> ⚠️ You must complete this step before syncing!

## Step 2: Sync

### Sync the entire library (all playlists)

```bash
uv run music-sync
```

- To exclude certain playlists, list them one per line in
  `data/apple_music/exclude_playlists.txt`.

### Sync a specific playlist

1. Parse the Apple Music library (if not already done):

```bash
uv run music-sync-parse-library
```

2. Sync a playlist by name:

```bash
uv run music-sync-playlist --name "Apple Music Playlist Name"
```

Pass `--help` to any of these commands to see the available options.

# Development

```bash
uv run pytest
uv run ruff check src tests
uv run pre-commit install
```

# Notes
- Syncing only adds songs to Spotify playlists
- Songs removed in Apple Music will not be removed from the Spotify playlist.
- Only playlists are synced

# TODO:
- [ ] Use cosine similarity of LLM embeddings to better evaluate match

# Related projects
- https://soundiiz.com
