# Git Hooks

From [Git docs](https://git-scm.com/docs/githooks#_description):

> Hooks are programs you can place in a hooks directory to trigger actions at certain points in git’s execution. Hooks that don’t have the executable bit set are ignored.

### Usage
To use any hook, execute the command provided command in the project root directory to link the script into the `.git/hooks` directory.


## Pre-Push Hook
From [Git docs](https://git-scm.com/docs/githooks#_pre_push):

> This hook is called by git-push and can be used to prevent a push from taking place.

### Content
Our pre-push hook shall prevent accidental pushes to protected branches like `main` and `gh-pages`.

### Installation
```sh
ln -s -f ../../.hooks/pre-push.sh ./.git/hooks/pre-push
chmod +x .git/hooks/pre-push
```
