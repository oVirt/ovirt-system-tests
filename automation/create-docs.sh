#!/bin/bash -xe

create_docs.create_docs() {
    # $1: Where to place the generated docs, default is docs-out

    local out_dir=${1:-docs-out}

    mkdocs build -f docs/mkdocs.yml -d "$out_dir"
}

create_docs.main() {
    local name="$(basename "${0%.*}")"
    if [[ "$name" = "check-docs" ]]; then
        # Alias for CI
        create_docs.check
        return
    fi
    create_docs.create_docs
}

create_docs.check() {
    local project="$PWD"
    local artifacts_dir="${project}/exported-artifacts"
    local docs_dir_name="docs-out"

    echo "Creating Docs"

    [[ -d "$artifacts_dir" ]] || mkdir "$artifacts_dir"
    create_docs.create_docs "${artifacts_dir}/${docs_dir_name}"
    # Generate html report
    cat > "${artifacts_dir}/index.html" <<EOF
    <html>
    <head>
        <li>
            <a href="${docs_dir_name}/index.html">Docs Page</a>
        </li>
    </head>
    </html>
EOF
}

create_docs.main
