# About this repo

## Summary
Synchronize Apple Music library with Spotify.

## Features
- Complete control over your data (data is only processed by Spotify's API, no third party)
- Supports incremental syncing by keeping track of what has been synced before
- Provides detailed reports on the syncing effectiveness by logging song matches and their associated similarity scores.
  See example below:

| Apple Song Name   | Apple Artist     | Apple Album            | Spotify Song Name   | Spotify Artist   | Spotify Album   | Spotify Track ID       |   Match Score |   Song Match Score | Artist Match Score | Album Match Score |
|:------------------|:-----------------|:-----------------------|:--------------------|:-----------------|:----------------|:-----------------------|--------------:|-------------------:|-------------------:|------------------:|
| Caruso            | Fiorella Mannoia | A te (Special Edition) | Caruso              | Fiorella Mannoia | A te            | 2kWftUZ8PxLQtRvrHX3cIe |          0.93 |               0.83 |               0.88 |               0.2 |

- Successfully matches various edge cases, such as artist collaborations (e.g. `&` in artist name or `feat.` in song name)

# Installation guide

## 1. Set up Spotify developer account & register app

These steps have been validated with the website's version as of 2021-01-17.

1. Go to https://developer.spotify.com/dashboard/ and create an account
2. Click on "CREATE AN APP"
3. Provide the app name & description of your choice, tick the terms of service and click "CREATE"
4. Click on "EDIT SETTINGS"
5. Under "Redirect URIs" put `http://localhost:9000/callback/` and `http://localhost:8090`
6. On the left side of the dashboard, underneath the description of your app, you will find your apps' "Client ID".
   Take note of it as you will need it in step 2.2.
7. Below your "Client ID" you will find an option to "SHOW CLIENT SECRET", click on it and take note of the value as you
   you will need it in step 2.2.

## 2. Set up the environment on your machine

### 2.1 Get the code & set environmental variables

The below instructions are for Linux or MacOS.

```commandline
git clone git@github.com:calyptis/MusicSync.git
cd MusicSync
source prepare_env.sh
```

### 2.2 Install module

Install pinned development dependencies using:

```
pip install -r requirements.txt
```

If you are using Conda to manage your Python environments:

```
conda env create -f environment.yml
```

Alternatively, if you are using an existing environment, you can install the module in [editable mode](https://setuptools.pypa.io/en/latest/userguide/development_mode.html), which includes only minimal dependencies:

```
pip install -e .
```


### 2.3 Specify your credentials

In the folder `credentials` create a file named `credentials.json`
where you specify the configurations you obtained in step 1.6 & 1.7.

The file has the following structure:

```python
{
	"client_id": "{your_client_id}",
	"client_secret": "{you_client_secret}",
	"redirect_uri": "http://localhost:9000/callback/",
	"redirect_flask_uri": "http://localhost:8090"
}
```

replace your client ID with value from step 1.6 and your client secret from step 1.7.


# User instructions

First and foremost
- open Music app (macOS or Windows, tested with app version `1.2.5.7`)
- Go to `File -> Library -> Export Library...`
- Save file as `Library.xml` in `data/apple_music/`

Only then, can your playlists be synced.

### To run the entire pipeline (parse Apply Music Library + sync it in its entirety)
```bash
python -m music_sync.main
```

### To sync a specific playlist
1. If Apple Music library has not yet been parsed:

```bash
python -m music_sync.apple_music.main
```

2. Sync a specific playlist

```bash
python -m music_sync.spotify.main --name "Apple Music Playlist Name"
```

# Notes
- Syncing a playlist only **adds** songs
  - Songs removed in the Apple Music playlist **will not** be **removed** from the Spotify playlist after syncing.

# Related projects
- https://soundiiz.com
