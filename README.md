[![MIT license](https://img.shields.io/badge/License-MIT-blue.svg)](https://lbesson.mit-license.org/) [![Netlify Status](https://api.netlify.com/api/v1/badges/40cc72d1-7f75-49f3-9b39-c8081ad8cc64/deploy-status)](https://app.netlify.com/sites/compassionate-allen-469116/deploys)

## 構成
- サイトはSphinxで動作
- 用語はdocs/words にプレーンに配置
- 書式は md か rst いずれでもよい

## install
### poetry

[poetryインストール](https://python-poetry.org/docs/#installation)

``` bash
poetry config --list
poetry config virtualenvs.in-project true
poetry install
```

### sphinx build

``` bash
sphinx-build docs/ docs/_build
```

### sphinx-autobuild

``` bash
poetry run poe doc
```