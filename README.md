# Office Render Skill

An agent skill (Claude Code or Codex) that renders PowerPoint decks to PDF and PNG on macOS through
Microsoft PowerPoint, without PowerPoint asking for file access every time a script touches a new
folder. Each project gets one render folder that PowerPoint is granted once.

一个 Claude Code / Codex skill：在 Mac 上用 PowerPoint 把 .pptx 渲染成 PDF 和 PNG，不再每换一个文件夹就弹
"授予文件访问权限"。每个项目一个固定的渲染文件夹，只授权一次。

## The problem

PowerPoint for Mac is sandboxed. When a script asks it, through AppleScript, to save into a folder it
hasn't been granted, it shows **Grant File Access** and waits. It remembers every folder once granted,
so rendering decks where they lie (a new meeting folder, a build folder, a temporary folder per
session) asks again and again. Worse, the dialog often sits unseen on another desktop while the render
hangs, and the screen jumps to PowerPoint whenever someone brings it forward.

## How it works

- **One render folder per project, `<project>/.office-render`.** The deck is copied there and PowerPoint
  never works anywhere else, so it asks once per project. A subfolder or worktree of a git repo maps to
  the main checkout, so every session and worktree of a repo shares the folder, and the folder keeps
  itself out of git.
- **Opening never prompts.** Copies are named `~$office-render-…`: PowerPoint's sandbox may read and
  write `~$*` files anywhere (the rule exists for Office's lock files). Only saving the PDF needs the
  grant, so the one-time dialog asks for the folder rather than a file.
- **The screen doesn't jump.** PowerPoint stays in the background; if it comes to the front anyway, it is
  hidden again. The exception is a dialog the user has to answer: that one is brought forward instead.
- **A stuck render explains itself.** If PowerPoint is waiting on a dialog, the script notices within
  seconds and says so, instead of hanging. Once the user grants access, the save that was waiting
  finishes by itself.
- **Nothing to install.** Python 3 standard library only (the `python3` that comes with macOS works);
  PNGs are drawn with macOS's own PDFKit.

Approaches that look simpler but don't work:

- **Office's containers.** Putting files in `~/Library/Group Containers/UBF8T346G9.Office` or
  `~/Library/Containers/com.microsoft.Powerpoint` stops PowerPoint asking, but macOS then asks the agent's
  app for "data from other apps" instead, again in every session, because Apple's app-group container
  protection can't be granted permanently.
- **Full Disk Access.** It would silence that second prompt, but it is far too broad a permission to give
  an agent just to render slides.

## Requirements

- macOS with Microsoft PowerPoint for Mac
- Python 3.9 or later
- An agent that runs shell commands, such as [Claude Code](https://claude.com/claude-code) or
  [Codex](https://developers.openai.com/codex)

## Install

### Claude Code

As a plugin (in Claude Code):

```
/plugin marketplace add ezoiHY/office-render-skill
/plugin install office-render@office-render
```

Or as a personal skill, which is easier to edit:

```bash
git clone https://github.com/ezoiHY/office-render-skill.git
ln -s "$PWD/office-render-skill/skills/office-render" ~/.claude/skills/office-render
```

### Codex

```bash
git clone https://github.com/ezoiHY/office-render-skill.git
mkdir -p ~/.agents/skills
ln -s "$PWD/office-render-skill/skills/office-render" ~/.agents/skills/office-render
```

## Usage

The agent follows [`SKILL.md`](skills/office-render/SKILL.md): ask it to render or check a deck. By hand:

```bash
S=skills/office-render/scripts/office_render.py
python3 $S --status --project .           # where the render folder is, and whether it is granted
python3 $S --grant --project .            # once per project: answer PowerPoint's dialog
python3 $S deck.pptx --project . --png    # PDF + one PNG per slide in .office-render/deck/
```

The first time, PowerPoint shows **Grant File Access**. Click **Select…**, select the `.office-render`
folder itself (it is hidden: press ⌘⇧. to show it, or select the project folder above it), then click
**Grant Access**. That project never asks again.

| Exit code | Meaning |
|---|---|
| 0 | Done (for `--status`: granted) |
| 2 | Bad arguments, no PowerPoint, or macOS doesn't let this app control PowerPoint |
| 3 | The render folder isn't granted yet: run `--grant` |
| 4 | PowerPoint is waiting on a dialog: answer it (`--grant` brings it forward) |
| 5 | PowerPoint couldn't open or export the file |

Other scripts can import it and call `export_pdf(deck, pdf, project=...)`, which raises `Stop` with the
exit code as `.code`. A skill can bundle a copy of the script this way, as
[pairs-group-meeting-skill](https://github.com/ezoiHY/pairs-group-meeting-skill) does for its renderer.
Everything that follows the convention shares one `.office-render` folder, and one grant, per project.

## 中文说明

**为什么老弹框**：PowerPoint for Mac 运行在沙盒里。脚本让它往一个没授权过的文件夹里存文件时，它会弹
"授予文件访问权限"并一直等着。授权过的文件夹它会记住，但每遇到一个新文件夹又要问一次，比如每次组会的新文件夹、
build 目录、每个会话的临时目录。框还经常弹在另一个桌面上，渲染就一直卡着。

**这个 skill 怎么做**：

- 每个项目固定一个渲染文件夹 `<项目>/.office-render`。deck 先复制进去，PowerPoint 只在这里打开和导出，
  所以每个项目只问一次。
- 副本用 `~$` 开头的名字：PowerPoint 的沙盒允许它在任何地方读写这种文件（本来是给 Office 锁文件用的），
  所以打开时永远不弹框。只有导出 PDF 需要授权，而且授权的是整个文件夹。
- 渲染时 PowerPoint 待在后台，不会跳到前台。只有需要你点授权时，它才会被调出来。

**第一次用**：PowerPoint 弹出"授予文件访问权限"时：

1. 点"选择…"。
2. 选中 `.office-render` 文件夹。它是隐藏文件夹，看不到就按 ⌘⇧. 显示；或者直接选上一层的项目文件夹。
3. 点"授予访问权限"。

这个项目以后不会再问。

**卡住时不要强制退出 PowerPoint**：几乎都是它在等一个对话框，强退会丢掉你自己打开的文档。

## Layout

```
.claude-plugin/                   plugin + marketplace manifests (Claude Code)
skills/office-render/
  SKILL.md                        when and how the agent renders, and what to tell the user
  scripts/office_render.py        the renderer: --status, --grant, render to PDF/PNG; export_pdf() for scripts
  assets/blank.pptx               the deck --grant exports to trigger the one-time dialog
tests/test_office_render.py       checks that need no PowerPoint (they also run on CI)
```
