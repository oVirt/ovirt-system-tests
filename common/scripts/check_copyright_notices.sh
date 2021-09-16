#!/bin/bash -e
# Check for copyright notices in files that do not also include an SPDX tag.

copyright_notices_files=$(git ls-files | xargs grep -d skip -il 'Copyright.*Red Hat')

copyright_notices_no_spdx_files=
[ -n "${copyright_notices_files}" ] && copyright_notices_no_spdx_files=$( \
    echo "${copyright_notices_files}" | \
    xargs grep -d skip -iL 'SPDX' \
) || true

if [ -n "${copyright_notices_no_spdx_files}" ]; then
    cat << __EOF__
[ERROR] : The following file(s) contain copyright/license notices, and do not contain an SPDX tag:
============================================================
${copyright_notices_no_spdx_files}
============================================================
Please replace the notices with an SPDX tag. How exactly to do this is language/syntax specific. You should include the following two lines in a comment:
============================================================
Copyright oVirt Authors
SPDX-License-Identifier: GPL-2.0-or-later
============================================================
__EOF__
    exit 1
fi
