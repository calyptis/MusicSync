# About this repo

Synchronize Apple Music library with Spotify.

Features:
- Supports incremental syncing by keeping track of what has been synced before
- Provides detailed reports on the syncing effectiveness by logging song matches and their associated similarity scores.
  See example below.

| Apple Song Name   | Apple Artist     | Apple Album            | Spotify Song Name   | Spotify Artist   | Spotify Album   | Spotify Track ID       |   Match Score |   Song Match Score |   Artist Match Score | Album Match Score |
|:------------------|:-----------------|:-----------------------|:--------------------|:-----------------|:----------------|:-----------------------|--------------:|-------------------:|---------------------:|------------------:|
| Caruso            | Fiorella Mannoia | A te (Special Edition) | Caruso              | Fiorella Mannoia | A te            | 2kWftUZ8PxLQtRvrHX3cIe |        0.9375 |           0.833333 |                0.875 |               0.2 |

- Handles various edge cases, such as artist collaborations (e.g. `&` in artist name or `feat.` in song name)

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

### 2.2 Specify your credentials

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

To run the entire pipeline (parse Apply Music Library + sync it in its entirety)
```bash
python src/main.py
```

To sync a specific playlist
1. If Apple Music library has not yet been parsed:

```bash
python src/apple_music/library.py
```

2. Sync a specific library

```bash
python src/spotify/sync.py --name "Apple Music Playlist Name"
```

# Related projects
- https://soundiiz.com
