# Contributing

👋 Welcome!

Thanks for contributing to TheGreatAgentHack!
This guide explains exactly how our team works with Git + GitHub.
Even if this is your first time using Git, just follow these steps.

📌 1. Before you start

Make sure you have:

A GitHub account

Git installed

VS Code installed

You have accepted the collaboration invite for this repo

📥 2. Clone the repository

Open a terminal and run:

```bash
git clone https://github.com/krishnanefx/TheGreatAgentHack.git
cd TheGreatAgentHack
```

Or in VS Code:
Ctrl/Cmd + Shift + P → "Git: Clone" → paste repo URL

🌱 3. Create your own branch (VERY IMPORTANT)

Never work directly on main.

Create a branch:

```bash
git checkout -b yourname-feature
```

Examples:

- krishnan-frontend-setup
- alice-api-endpoints
- minh-login-page

🛠️ 4. Make changes locally

Edit files in VS Code

Keep commits small and focused

Save often

💾 5. Commit your work

Stage and commit:

```bash
git add .
git commit -m "feat: short description of what you did"
```

Commit message format:

- feat: new feature
- fix: bug fix
- docs: documentation
- style: formatting
- chore: misc cleanup

Examples:

- feat: add login form
- fix: correct API url
- docs: update README

⬆️ 6. Push your branch

Push your branch to GitHub:

```bash
git push -u origin your-branch-name
```

🔀 7. Open a Pull Request (PR)

Go to GitHub → Your branch → Compare & pull request

Your PR should include:

Title

Short but descriptive.
Example: feat: add user authentication

Description

What you changed

Why you changed it

How to test your change

Example:

Implemented login form and validation.

To test:

```bash
npm install
npm start
# Then open /login page in browser
```


Request a teammate to review your PR.

👀 8. Review process

A teammate will:

Read your changes

Suggest improvements (if any)

Approve the PR

Please be responsive to comments.

🔁 9. Update your PR (if needed)

If reviewers request changes:

Make edits

Commit again

```bash
git add .
git commit -m "fix: address review comments"
git push
```

Your PR updates automatically.

✅ 10. Merge the PR

After approval:

Click “Merge pull request”

Use “Squash and merge” unless there’s a reason not to

Delete your branch (optional)

Your code is now part of the project!

🔄 11. Keep your local main up to date

Every day before starting work:

```bash
git checkout main
git pull origin main
```

If your branch is old, update it:

```bash
git checkout your-branch
git merge origin/main
```

or (cleaner, but advanced):

```bash
git rebase origin/main
```

🧨 12. Handling merge conflicts (beginner version)

If Git shows a conflict:

Open the conflicted file

VS Code will show:

```
<<<<<<< HEAD
your version
=======
other version
>>>>>>> main
```

Keep the correct version

Save file

Then:

```bash
git add <file>
git commit
```

📚 13. Team conventions

- Branch names: yourname-feature or yourname/feature
- Commit messages: Follow the feat/fix/docs/chore pattern
- No direct pushes to main
- 1 approval required before merging
- PR description must include testing steps

🙌 Need help?

If you're stuck, just ask in the team chat or open an issue.
We are all learning!