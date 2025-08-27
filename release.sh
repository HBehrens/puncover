#!/usr/bin/env bash

# Script used to execute a puncover release:
#
# 1. Update the version in the code
# 2. Commit the change
# 3. Tag the commit
# 4. Push the commit and the tag
# 5. Build the package
# 6. Upload the package to PyPI
# 7. Create a release on GitHub
# 8. Upload the package to the release on GitHub
#
# It can be run for example like so:
#
# PUNCOVER_VERSION=0.1.0 ./release.sh

set -euo pipefail

if [[ -z "${PUNCOVER_VERSION:-}" ]]; then
    echo "PUNCOVER_VERSION must be set"
    exit 1
fi

# confirm that the pypi token is set
if [[ -z "${PYPI_TOKEN:-}" ]]; then
    echo "PYPI_TOKEN must be set"
    exit 1
fi

# check if tag already exists
if git rev-parse -q --verify "refs/tags/${PUNCOVER_VERSION}"; then
    echo "Tag ${PUNCOVER_VERSION} already exists"
    exit 1
fi

uv version ${PUNCOVER_VERSION}
git add . && git commit -m "Bump version to ${PUNCOVER_VERSION}"
git tag -a {-m=,}${PUNCOVER_VERSION}
rm -rf dist
uv build

while true; do
    read -p "Ready to push to GitHub and publish to PyPi? (y/n): " yn
    case $yn in
        [Yy]* ) echo "Proceeding..."; break;;
        [Nn]* ) echo "Exiting..."; exit;;
        * ) echo "Invalid response. Please answer y or n.";;
    esac
done

git push && git push --tags
uv publish --token=${PYPI_TOKEN} dist/*
gh release create --generate-notes ${PUNCOVER_VERSION}
gh release upload ${PUNCOVER_VERSION} dist/*
