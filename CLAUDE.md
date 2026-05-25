# NOC_Beam project notes

## Build output destination

**Always zip the built `dist/NOC_Beam/` folder to `E:\NOC_Beam\NOC_Beam.zip`.**

Never zip to anywhere else — not into the repo, not to the user's Desktop, not
to a timestamped sibling folder. The boss demo machine and the user's launch
path both look at `E:\NOC_Beam\NOC_Beam.zip` (the user unzips it back into
`E:\NOC_Beam\NOC_Beam\` to run). Writing the zip anywhere else leaves a stale
copy at the canonical path.

The standard build flow on this machine:

```powershell
cd E:\NOC_Beam\Eyebeam\python-app
pyinstaller --clean --noconfirm build\noc_beam.spec
Compress-Archive -Path dist\NOC_Beam\* -DestinationPath E:\NOC_Beam\NOC_Beam.zip -Force
```

The `-Force` overwrites the existing zip in place — that's the intent.
