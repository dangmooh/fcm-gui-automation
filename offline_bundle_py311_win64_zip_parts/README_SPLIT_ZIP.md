# Split Offline Bundle

This folder contains `offline_bundle_py311_win64.zip` split into parts smaller
than 20 MB.

Move every file named:

```text
offline_bundle_py311_win64.zip.part001
offline_bundle_py311_win64.zip.part002
...
```

to the same folder on the offline PC.

Then run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\reassemble_zip.ps1
```

The script recreates:

```text
offline_bundle_py311_win64.zip
```

After that, extract the zip and follow `README_OFFLINE_INSTALL.md`.
