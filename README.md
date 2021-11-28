[![MIT license](https://img.shields.io/badge/License-MIT-blue.svg)](https://lbesson.mit-license.org/) [![Netlify Status](https://api.netlify.com/api/v1/badges/40cc72d1-7f75-49f3-9b39-c8081ad8cc64/deploy-status)](https://app.netlify.com/sites/compassionate-allen-469116/deploys)

## poetry

[poetryインストール](https://python-poetry.org/docs/#installation)

## install

``` bash
poetry config --list
poetry config virtualenvs.in-project true
poetry install
```

## sphinx build

``` bash
sphinx-build docs/ docs/_build
```

## sphinx-autobuild

``` bash
poetry run poe doc
```