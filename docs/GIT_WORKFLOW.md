# Overfield — Git & GitHub Workflow

**Project:** Overfield
**Audience:** All team members
**Status:** Active

This document defines the Git branching model, commit conventions, tagging, and the
GitHub workflow (including the temporary sandbox repo and the future hackathon migration).

> **Rule 0 — Never rewrite shared history.** No `git push --force`, no `git reset --hard`
> on shared branches, no rebasing published commits, no changing author dates. The team must
> follow the official NASA Space Apps rules concerning pre-event work and repository history.

---

## 1. Branch model overview

| Branch | Type | Purpose | Lifetime |
|---|---|---|---|
| `main` | Long-lived | Stable, approved, demo-ready code. Every commit on `main` is a reviewed milestone. | Permanent |
| `develop` | Long-lived | Integration branch. Phase work is merged here first and validated before reaching `main`. | Permanent |
| `phase/<n>-<name>` | Long-lived (per phase) | One branch per development phase. All work for that phase lands here. | Until phase is merged & approved |
| `feat/...`, `fix/...`, `chore/...` | Optional short-lived | Small units of work branched off the current phase branch. | Days |

**Flow:** `feature` → `phase/*` → `develop` → `main`

- `main` is the **stable** branch — it should always be in a demonstrable state.
- `develop` is the **integration** branch — completed phase work is combined and tested here.
- `phase/*` branches isolate each phase so the team can work without destabilising
  `develop` or `main`.

### Defined phase branches

These names are reserved for the project. Create each one **only when that phase starts**.

| Phase | Branch |
|---|---|
| 0 | `phase/0-documentation-review` |
| 1 | `phase/1-foundation` |
| 2 | `phase/2-farm-management` |
| 3 | `phase/3-nasa-integration` |
| 4 | `phase/4-environmental-engine` |
| 5 | `phase/5-rotation-engine` |
| 6 | `phase/6-simulation` |
| 7 | `phase/7-dashboard` |
| 8 | `phase/8-verification-gamification` |
| 9 | `phase/9-final-integration` |

> **Do not create future phase branches prematurely.** A phase branch should be created
> from the current state of `develop` at the moment the phase begins.

---

## 2. Daily work

### 2.1 Start of day / sync

```bash
git checkout develop
git pull --ff-only origin develop          # fast-forward only, never rewrite
git checkout phase/0-documentation-review
git merge --ff-only develop                # bring latest integration work in (if any)
```

### 2.2 Make changes during a phase

```bash
git checkout phase/0-documentation-review
# ... edit files ...
git add -A
git status                                 # ALWAYS review what will be committed
git diff --cached                          # ALWAYS review the actual diff
git commit -m "docs(phase-0): clarify data provenance for SMAP ingestion"
```

Commit **often and small**. One logical change per commit.

### 2.3 Commit message convention

```
<type>(<scope>): <short imperative summary>
```

| Type | Use for |
|---|---|
| `docs` | Documentation only |
| `feat` | New feature |
| `fix` | Bug fix |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `test` | Adding or correcting tests |
| `chore` | Build, tooling, dependencies, config |
| `style` | Formatting only |
| `perf` | Performance improvement |

Examples:

```
docs(phase-0): add architecture decision for PostGIS
feat(phase-2): implement farm boundary GeoJSON validation
fix(phase-3): handle SMAP ingestion timeouts
chore(phase-1): pin Node 20 in .nvmrc
```

---

## 3. Creating a new phase branch

When a phase is ready to start, branch from the latest `develop`:

```bash
# 1. Make sure develop is current
git checkout develop
git pull --ff-only origin develop

# 2. Create and switch to the new phase branch
git checkout -b phase/1-foundation develop

# 3. Publish it so the team can collaborate
git push -u origin phase/1-foundation
```

To create a future phase branch the same way:

```bash
git checkout develop
git pull --ff-only origin develop
git checkout -b phase/3-nasa-integration develop
git push -u origin phase/3-nasa-integration
```

---

## 4. Merging a completed phase into `develop`

Use a **no-fast-forward merge** so each phase leaves a visible integration point in
history (helps traceability and the future audit).

```bash
# 1. Ensure the phase branch is pushed and tests pass locally
git checkout phase/1-foundation
git push origin phase/1-foundation

# 2. Update develop first
git checkout develop
git pull --ff-only origin develop

# 3. Merge the phase with an explicit merge commit
git merge --no-ff phase/1-foundation -m "merge(phase-1): integrate foundation into develop"

# 4. Push
git push origin develop
```

If there are conflicts, resolve them in the working tree, `git add` the resolved files,
then `git commit` to complete the merge. **Never** resolve conflicts by force-pushing.

---

## 5. Milestone tags

Tags mark reviewable milestones. They are **annotated** so they carry an author, date,
and message. This is the honest record of when work happened.

```bash
# Tag a milestone on a specific commit
git tag -a phase-0-review-complete -m "Phase 0 documentation review complete"
git push origin phase-0-review-complete

# Later milestones
git tag -a phase-1-complete -m "Phase 1 foundation complete and integrated"
git push origin phase-1-complete
```

> **Phase 0 is NOT approved yet.** Do **not** create a `phase-0-approved` tag until the
> review is actually signed off by the team.

List / inspect tags:

```bash
git tag -l
git show phase-0-review-complete
```

---

## 6. Updating `main` after an approved phase

`main` only moves forward when a phase is **approved**.

```bash
git checkout main
git pull --ff-only origin main

# Merge the validated integration branch
git merge --no-ff develop -m "release(phase-0): promote approved Phase 0 to main"
git push origin main

# Mark the milestone
git tag -a phase-0-approved -m "Phase 0 approved and promoted to main"
git push origin phase-0-approved
```

> Create the `phase-0-approved` tag **only after** the Phase 0 review is approved.

---

## 7. Pushing changes to GitHub

```bash
# Push the current branch
git push

# Push a new branch and set upstream
git push -u origin <branch-name>

# Push all branches
git push origin --all

# Push all tags
git push origin --tags
```

The existing `origin` remote is `https://github.com/Amr-767/nasa.git` and must remain untouched. The Overfield repository is `https://github.com/Amr-767/Overfield.git`; add it separately as `overfield`. Verify remotes before pushing:

```bash
git remote -v
```

---

## 8. Reverting a broken commit safely

**Golden rule:** on shared branches, prefer *reverting* (which adds a new commit) over
*resetting* (which destroys history).

### 8.1 Revert a normal commit

```bash
git revert <bad-commit-hash>       # creates a new commit that undoes it
git push origin <branch>
```

### 8.2 You made a bad commit but have NOT pushed yet

```bash
# Keep the work, un-commit it, leave changes staged
git reset --soft HEAD~1

# Or un-commit and unstage, keep the file changes
git reset --mixed HEAD~1
```

### 8.3 You committed a bad merge (already pushed)

```bash
git revert -m 1 <merge-commit-hash>
git push origin <branch>
```

### 8.4 Never do this on shared branches

```bash
git push --force              # FORBIDDEN
git push --force-with-lease   # FORBIDDEN on shared branches
git reset --hard <hash>       # FORBIDDEN after the commit is published
```

If a secret was accidentally committed, treat it as compromised: **rotate the secret**,
then remove it from the working tree and history carefully with the team's agreement
(`git filter-repo`), and force-update only after coordinating with everyone.

---

## 9. Preserving Git history

- Never squash an entire phase into a single commit just to "tidy up".
- Use `--no-ff` merges so phase boundaries remain visible.
- Do not edit commit dates, author identities, or messages of published commits.
- Do not rebase branches that others have already pulled.
- Keep merge commits; they are the historical record of when integration happened.

Verify history integrity at any time:

```bash
git log --graph --oneline --decorate --all
git shortlog -sn
```

---

## 10. Existing repository remote

The current checkout's existing remote remains untouched:

| Setting | Value |
|---|---|
| Repository | `https://github.com/Amr-767/nasa.git` |
| Remote name | `origin` |

The Overfield repository is separate and should use a distinct `overfield` remote. Do not rename or repoint `origin`.

---

## 11. Publishing Overfield

The Overfield GitHub repository is a separate destination. Keep `origin` unchanged. Add Overfield under a distinct remote name and publish only the reviewed branch.

```bash
# 1. Add Overfield as a second remote (keep origin unchanged)
git remote add overfield https://github.com/Amr-767/Overfield.git

# 2. Verify both remotes
git remote -v

# 3. Push the reviewed current phase branch only
git push -u overfield phase/4-environmental-engine

# 4. Fetch to confirm the branch was published
git fetch overfield
git branch --all
git log --oneline --all
```

Notes:

- Initialize the Overfield repository empty to avoid unrelated histories.
- Do not publish every branch or tag by default; push only those intentionally reviewed.
- **Do not rewrite commit dates** and **do not disguise when work was performed.** All
  commits carry their honest author/committer dates. The team must follow the official
  NASA Space Apps rules concerning pre-event work and repository history.
- Do not rename or repoint the existing `origin`; Overfield is an additional remote.
- Confirm the Overfield repository visibility and collaborator access on GitHub.

---

## 12. Quick reference

```bash
# Inspect
git status
git branch --all
git remote -v
git log --oneline --all
git log --graph --oneline --decorate --all

# Branch
git checkout develop
git checkout -b phase/N-name develop
git push -u origin phase/N-name

# Integrate a phase
git checkout develop
git merge --no-ff phase/N-name -m "merge(phase-N): ..."

# Promote to main (after approval)
git checkout main
git merge --no-ff develop -m "release(phase-N): ..."

# Tag a milestone
git tag -a <tag> -m "<message>"
git push origin <tag>

# Push everything
git push origin --all
git push origin --tags

# Undo safely
git revert <hash>
```
