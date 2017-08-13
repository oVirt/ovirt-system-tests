#!/bin/bash -xe

create_docs.create_docs() {
    # $1: Where to place the generated docs, default is docs-out

    local out_dir=${1:-docs-out}

    mkdocs build -f docs/mkdocs.yml -d "$out_dir"
}

create_docs.main() {
    create_docs.create_docs
}

if [[ "$0" = "$BASH_SOURCE" ]]; then
    create_docs.main
fi
