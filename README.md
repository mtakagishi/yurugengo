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