# Pull Requests

Create a pull request on GitHub by forking this repository, cloning it to your computer, and
creating a new branch. More info on PRs with GitHub can be found
[here](https://opensource.com/article/19/7/create-pull-request-github).

# Pre-Commit

This repo has certain style guidelines that must be followed. [pre-commit](https://pre-commit.com/)
will automatically handle these for you on all staged files when you commit.

Setup `pre-commit` before committing to a PR by executing the following commands in shell in the
repo directory:
```
$ make install
$ pre-commit install
```
If you're setting up `pre-commit` after committing, you'll also need to run it on all files with:
```
$ pre-commit run --all-files
```
