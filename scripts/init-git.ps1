<#
.SYNOPSIS
    Safely initialize git for the ReClaw 2.0 repo following OpenClaw / clawd discipline.

.DESCRIPTION
    - Inits the repo if not already a git repo
    - Respects the existing .gitignore (never commits .env, data/runs/, data/sessions/, outputs/, secrets)
    - Does a clean first commit with good message
    - Shows status before and after

.USAGE
    From PowerShell, in the reclaw directory:

    .\scripts\init-git.ps1

    Or with a custom message:

    .\scripts\init-git.ps1 -CommitMessage "reclaw: initial structure with Researcher, Analyst, Gateway + security gates"

.NOTES
    After this runs, you still need to:
    - Set your name/email if not already global
    - Add a remote (GitHub, Hetzner bare repo, etc.)
    - git push
#>

param(
    [string]$CommitMessage = "reclaw: initial production structure for Rural Data Faceless Channel agent swarm. Researcher + Analyst + light Orchestrator + Gateway control plane. Session isolation, SOUL.md identities, approval gates, Obsidian writer. Pike/Winslow seeds. OpenClaw-aligned patterns."
)

$ErrorActionPreference = "Stop"

Write-Host "=== ReClaw git initializer ===" -ForegroundColor Cyan
Write-Host "Working in: $(Get-Location)" -ForegroundColor Gray

# Make sure we're in the right place (has key files)
if (-not (Test-Path "SOUL.md") -or -not (Test-Path "AGENTS.md") -or -not (Test-Path ".gitignore")) {
    Write-Error "This doesn't look like the reclaw root. cd to the reclaw directory first."
    exit 1
}

# Check for real .env (should be ignored)
if (Test-Path ".env") {
    Write-Host "Note: .env exists (it should be gitignored — good)." -ForegroundColor Yellow
}

# Check if already a git repo
if (Test-Path ".git") {
    Write-Host "This is already a git repository." -ForegroundColor Green
    git status --short
    exit 0
}

Write-Host "`nInitializing new git repository..." -ForegroundColor Green
git init

# Set sensible defaults if not configured globally
$gitName = git config --get user.name
$gitEmail = git config --get user.email

if (-not $gitName) {
    Write-Host "No global git user.name found. Setting a placeholder (change it!)." -ForegroundColor Yellow
    git config user.name "Jason Boyd"
}
if (-not $gitEmail) {
    Write-Host "No global git user.email found. Setting a placeholder (change it!)." -ForegroundColor Yellow
    git config user.email "jason@example.local"
}

Write-Host "`nCurrent git config:" -ForegroundColor Gray
git config --list --local | Select-String -Pattern "user\.(name|email)"

Write-Host "`nAdding all files (respecting .gitignore)..." -ForegroundColor Green
git add -A

Write-Host "`n=== Files that will be committed ===" -ForegroundColor Cyan
git status --short

Write-Host "`nCreating initial commit..." -ForegroundColor Green
git commit -m $CommitMessage

Write-Host "`n=== Done ===" -ForegroundColor Cyan
Write-Host "Repo initialized and first commit created." -ForegroundColor Green

Write-Host "`nNext steps (recommended):" -ForegroundColor Yellow
Write-Host "1. Review the commit:   git log --oneline -5"
Write-Host "2. Set real identity if the placeholders were used:"
Write-Host "      git config user.name 'Your Real Name'"
Write-Host "      git config user.email 'you@yourdomain.com'"
Write-Host "3. Add a remote (example for GitHub):"
Write-Host "      git remote add origin https://github.com/yourname/reclaw.git"
Write-Host "      git branch -M main"
Write-Host "      git push -u origin main"
Write-Host "4. For Hetzner deployment later, you can also push to a bare repo on the server or just rsync the source tree."
Write-Host ""
Write-Host "Remember the clawd discipline:"
Write-Host "  - git status before big work"
Write-Host "  - git add -A + commit after meaningful changes"
Write-Host "  - Never commit .env or runtime data"
