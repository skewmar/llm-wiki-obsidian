# macOS LaunchAgent — Always-On Watcher

Runs `watch.py --fetch` in the background on login. Restarts on crash.

## Install

```bash
# 1. Set your repo path in the plist
REPO=$(pwd)
sed -i '' "s|REPO_PATH|$REPO|g" launchagent/com.skewmar.knowledgegraph.plist

# 2. Copy to LaunchAgents
cp launchagent/com.skewmar.knowledgegraph.plist ~/Library/LaunchAgents/

# 3. Load
launchctl load ~/Library/LaunchAgents/com.skewmar.knowledgegraph.plist
```

## Check Status

```bash
launchctl list | grep skewmar
tail -f launchagent/watch.log
```

## Uninstall

```bash
launchctl unload ~/Library/LaunchAgents/com.skewmar.knowledgegraph.plist
rm ~/Library/LaunchAgents/com.skewmar.knowledgegraph.plist
```
