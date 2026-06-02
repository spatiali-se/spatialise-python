## Setting up the environment

### With Rye

We use [Rye](https://rye.astral.sh/) to manage dependencies because it will automatically provision a Python environment with the expected Python version. To set it up, run:

```sh
$ ./scripts/bootstrap
```

Or [install Rye manually](https://rye.astral.sh/guide/installation/) and run:

```sh
$ rye sync --all-features
```

You can then run scripts using `rye run python script.py` or by activating the virtual environment:

```sh
# Activate the virtual environment - https://docs.python.org/3/library/venv.html#how-venvs-work
$ source .venv/bin/activate

# now you can omit the `rye run` prefix
$ python script.py
```

### Without Rye

Alternatively if you don't want to install `Rye`, you can stick with the standard `pip` setup by ensuring you have the Python version specified in `.python-version`, create a virtual environment however you desire and then install dependencies using this command:

```sh
$ pip install -r requirements-dev.lock
```

## Modifying/Adding code

This SDK is maintained by hand. Edit the files under `src/spatialise/` directly — there is no code
generator, so your changes are the source of truth. After changing the public API, keep
`openapi/openapi.yml` (used by the test mock server, see [Running tests](#running-tests)) and the tests
under `tests/` in sync with your change.

## Adding and running examples

All files in the `examples/` directory can be freely edited or added to.

```py
# add an example to examples/<your-example>.py

#!/usr/bin/env -S rye run python
…
```

```sh
$ chmod +x examples/<your-example>.py
# run the example against your api
$ ./examples/<your-example>.py
```

## Using the repository from source

If you’d like to use the repository from source, you can either install from git or link to a cloned repository:

To install via git:

```sh
$ pip install git+ssh://git@github.com/spatiali-se/spatialise-python#development.git
```

Alternatively, you can build from source and install the wheel file:

Building this package will create two files in the `dist/` directory, a `.tar.gz` containing the source files and a `.whl` that can be used to install the package efficiently.

To create a distributable version of the library, all you have to do is run this command:

```sh
$ rye build
# or
$ python -m build
```

Then to install:

```sh
$ pip install ./path-to-wheel-file.whl
```

## Running tests

Most tests require a [Prism mock server](https://github.com/stoplightio/prism) running against the
OpenAPI spec at `openapi/openapi.yml`. `./scripts/test` starts one for you (on `127.0.0.1:4010`) if it
isn't already running:

```sh
$ ./scripts/test
```

To run the mock server by hand against the local spec:

```sh
# you will need npm installed
$ ./scripts/mock
```

## Linting and formatting

This repository uses [ruff](https://github.com/astral-sh/ruff) and
[black](https://github.com/psf/black) to format the code in the repository.

To lint:

```sh
$ ./scripts/lint
```

To format and fix all ruff issues automatically:

```sh
$ ./scripts/format
```

## Publishing and releases

This SDK is hand-maintained — there is no Stainless generator and no release-please
automation (both were removed when the repo was taken in-house). Releases are cut by
a maintainer, by hand:

1. Bump the version in **both** `src/spatialise/_version.py` and `pyproject.toml`.
2. Add a `## <version>` section to `CHANGELOG.md` describing the change.
3. Commit (`chore(release): <version>`) and merge to the default branch.
4. Create a **GitHub Release** with tag `v<version>` (e.g. `v0.3.0`). Publishing
   the Release triggers [the `Publish PyPI` workflow](https://www.github.com/spatiali-se/spatialise-python/actions/workflows/publish-pypi.yml)
   (`.github/workflows/publish-pypi.yml`), which builds with Rye and runs
   `bin/publish-pypi` using the `SPATIALISE_SOIL_PREDICTION_PYPI_TOKEN` /
   `PYPI_TOKEN` secret. No regenerated OpenAPI spec or Stainless tooling is involved.

The actual publish is a deliberate manual step — opening the GitHub Release is what
ships the package; nothing publishes on a plain branch merge.

### Publish manually (fallback)

If the workflow can't be used, run `bin/publish-pypi` locally with `PYPI_TOKEN` set on
the environment (after `rye build`).
