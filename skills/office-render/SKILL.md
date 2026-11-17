---
name: office-render
description: Render PowerPoint decks (.pptx) to PDF and PNG on macOS through Microsoft PowerPoint without the recurring "Grant File Access" / 授予访问权限 prompts. Each project gets one fixed render folder (<project>/.office-render) that PowerPoint is allowed into once, and every render is staged there. Use this whenever you are about to open, export, convert, render, preview or screenshot a .pptx with PowerPoint on a Mac (AppleScript or osascript, "save as PDF", visual QA of slides), when a render hangs because PowerPoint is waiting on a dialog, or when the user complains that PowerPoint keeps asking for file access (授权) or jumping to the front.
---

# Office render

PowerPoint for Mac runs in a sandbox. When a script makes it save into a folder it has not been
granted, it shows "Grant File Access" and waits for the user. Once a folder is granted, PowerPoint
remembers it, along with everything inside. So rendering decks where they lie (a new meeting
folder, a build folder, the session scratchpad) asks again for every new folder, and the dialog
often waits unseen on another desktop while the render hangs. The fix is one render folder per
project, `<project>/.office-render`, granted once, with all PowerPoint work happening inside it.

`scripts/office_render.py` does the whole job using only the Python 3 standard library, so plain
`python3` runs it.

## Workflow

1. **Name the project.** Pass `--project <your primary working directory>` (the folder this session
   started in) on every call, so the render folder doesn't change with the shell's current directory.
   Inside a git repo the script uses the main checkout, so every session and worktree of the repo
   shares one folder.
2. **First time in a project.** If `--status` says `granted: no` (exit 3) or a render exits 3,
   tell the user before running anything, in their language, that PowerPoint will ask once:
   - in "Grant File Access", click **Select…** (选择…);
   - make sure the folder `.office-render` itself is selected, not a file inside it. It is a hidden
     folder, so if the panel doesn't show it, press ⌘⇧. (Command-Shift-period), or select the project
     folder above it instead (a grant covers every subfolder);
   - click **Grant Access** (授予访问权限).

   This project won't ask again. Then run `--grant`. It brings PowerPoint to the front only while
   the dialog is up, waits up to five minutes for the click, and hands focus back afterwards. If a
   render already left a dialog waiting, `--grant` shows that one first, and once the user grants it,
   the stuck save finishes by itself.
3. **Render.**
   ```bash
   python3 <this skill>/scripts/office_render.py deck.pptx --project <root> --png
   ```
   It prints `PDF: …` and one `PNG: …` per slide, written to `<root>/.office-render/<deck name>/`
   (or `--out DIR`). Look at the PNGs, or Read the PDF. Several decks can go in one call. Allow a
   long timeout or run it in the background, because decks with embedded video take a minute.
   From Python, `export_pdf(deck, pdf, project=...)` in the same script does one render and raises
   `Stop` with the exit code below as `.code`.

## When it stops

| Exit | Meaning | What to do |
|---|---|---|
| 3 | The render folder isn't granted yet | Step 2 |
| 4 | PowerPoint is waiting on a dialog. Either its access was lost (the folder was deleted or moved, or PowerPoint was reset) or it is a sign-in, update or recovery prompt. The window may be on another desktop | Tell the user, then run `--grant`, which brings the dialog forward and waits |
| 5 | PowerPoint couldn't open or export the file | Read the message; check that the file opens |
| 2 | No PowerPoint, bad arguments, or macOS won't let this app control PowerPoint | Follow the message |

Don't force-quit PowerPoint when a render seems stuck. It is almost always a dialog, and killing
PowerPoint throws away the user's own open decks. Ask the user instead.

## Why it works this way

- **One folder per project, never the deck's own folder.** Every new folder PowerPoint touches costs
  the user a dialog. Copying the deck into the render folder makes it irrelevant where the deck lives.
- **Copies are named `~$office-render-…`.** PowerPoint's sandbox may read and write `~$*` files
  anywhere (the rule exists for Office's lock files), so opening the copy never prompts. Only saving
  the PDF needs the grant, which is why the one-time dialog asks for the folder rather than for a file.
- **Not Office's containers.** Files in `~/Library/Containers/com.microsoft.Powerpoint` or
  `~/Library/Group Containers/UBF8T346G9.Office` don't make PowerPoint ask, but macOS then asks the
  app the agent runs in for "data from other apps", again in every session.
- **No Full Disk Access as a workaround.** It is far too broad a permission to give an agent's app
  just for rendering.
- **Focus stays with the user.** A normal render never activates PowerPoint, and if PowerPoint comes
  to the front anyway (when it launches, say), the script hides it again so the screen doesn't jump.
- **The grant is tied to this exact folder.** Deleting `.office-render` loses it; the next render
  then exits 3 or 4, and `--grant` sets it up again. The folder is excluded from git by its own
  `.gitignore`.

## Other renderers and Office apps

- A renderer from another skill that opens decks in PowerPoint where they sit will keep prompting for
  every new folder. For the PowerPoint step, prefer this script, or move that renderer to the same
  convention: bundle a copy of `office_render.py` and call `export_pdf()`, the way
  pairs-group-meeting's `render.py` does. Renderers that follow it share one `.office-render` folder,
  and so one grant, per project.
- Word and Excel are sandboxed the same way. If you have to script them, open and save inside the same
  `.office-render` folder. Each app needs its own one-time grant.
- `--render-dir DIR` uses exactly that folder instead, for example one folder shared by several
  projects.
