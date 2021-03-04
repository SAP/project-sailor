#!/usr/bin/env bash

# adapted from https://gist.github.com/vlucas/8009a5edadf8d0ff7430

protected_branches=('main' 'gh-pages')

is_destructive='force|delete|\-f'

current_branch=$(git symbolic-ref HEAD | sed -e 's,.*/\(.*\),\1,')
push_command=$(ps -ocommand= -p $PPID)

do_exit() {
  printf "[Policy] Never push code directly to the %s branch! (Prevented with pre-push hook.)\n\n" "$protected_branch"
  exit 1
}

for protected_branch in "${protected_branches[@]}"; do
  will_remove_protected_branch=':'$protected_branch

  if [[ $push_command =~ $is_destructive ]] && [ $current_branch = $protected_branch ]; then
    do_exit
  fi

  if [[ $push_command =~ $is_destructive ]] && [[ $push_command =~ $protected_branch ]]; then
    do_exit
  fi

  if [[ $push_command =~ $will_remove_protected_branch ]]; then
    do_exit
  fi

  # Prevent ALL pushes to protected_branch
  if [[ $push_command =~ $protected_branch ]] || [ $current_branch = $protected_branch ]; then
    do_exit
  fi
done

unset do_exit

exit 0
