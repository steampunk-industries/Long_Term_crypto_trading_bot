# VSCode File Watcher Issue Fix

## Problem

Visual Studio Code was displaying an error message:
```
"Visual Studio Code is unable to watch for file changes in this large workspace (ENOSPC)"
```

This happens when VSCode runs out of available inotify watches in Linux, which are needed to monitor files for changes.

## Fixes Applied

### 1. Increased System-Wide inotify Watch Limit

The inotify watch limit has been increased from 29,805 to 524,288 by adding this line to `/etc/sysctl.conf`:

```
fs.inotify.max_user_watches=524288
```

And applying it with:
```
sudo sysctl -p
```

### 2. Created VSCode Settings to Exclude Large Directories 

Created `.vscode/settings.json` with the following configuration:

```json
{
  "files.watcherExclude": {
    "**/.git/objects/**": true,
    "**/.git/subtree-cache/**": true,
    "**/node_modules/*/**": true,
    "**/crypto_venv/**": true,
    "**/aws_venv/**": true,
    "**/myenv/**": true,
    "**/data/**": true,
    "**/logs/**": true,
    "**/deploy/**": true,
    "**/microservices/**": true,
    "**/reports/**": true,
    "**/cleanup_backup_*/**": true,
    "**/cleanup_reports/**": true
  },
  "editor.fontFamily": "Droid Sans Mono, Droid Sans Fallback"
}
```

This excludes large directories from file watching, significantly reducing the number of watches needed.

## Memory Impact

Each file watch takes approximately 1,080 bytes of memory:
- At the max setting of 524,288 watches, this could use up to ~540 MB of RAM
- This is typically not an issue for most systems, but can be reduced if needed

## What to Do If the Error Persists

1. Restart VSCode to apply the settings
2. Close other applications that might be using file handles
3. If memory is constrained, consider a lower watch limit (e.g., 262,144)
4. Add more directories to the `files.watcherExclude` list if needed
5. For projects with very large numbers of files, consider using a `.gitignore`-style approach to exclude certain folders

## Additional Notes

- The "Droid Sans Mono, Droid Sans Fallback" font setting also helps with displaying Chinese characters in Ubuntu
- Each VSCode instance uses separate file watches, so running multiple instances will consume more watches
