#!/usr/bin/env bash

set -euo pipefail
exec 3>&1 # New file descriptor to stdout

BASE_URL="https://dev.azure.com/\
python-discord/${SYSTEM_TEAMPROJECTID}/_apis/build/builds?\
queryOrder=finishTimeDescending&\
resultFilter=succeeded&\
\$top=1&\
repositoryType=${BUILD_REPOSITORY_PROVIDER}&\
repositoryId=${BUILD_REPOSITORY_NAME}&\
api-version=5.0"

get_build() {
    set -e # Poor Ubuntu LTS doesn't have Bash 4.4's inherit_errexit

    local branch="${1:?"get_build: argument 1 'branch' is unset"}"
    local url="${BASE_URL}&branchName=${branch}"

    printf '%s\n' "Retrieving the latest successful build using ${url}" >&3

    local response
    response="$(curl -sSL "${url}")"

    if [[ -z "${response}" ]] \
        || ! count="$(printf '%s' "${response}" | jq -re '.count')" \
        || (( "${count}" < 1 ))
    then
        return 1
    else
        printf '%s' "${response}"
    fi
}

# Get the previous commit
if [[ "${BUILD_REASON}" = "PullRequest" ]]; then
    if ! prev_commit="$(
            get_build "${BUILD_SOURCEBRANCH}" \
            | jq -re '.value[0].triggerInfo."pr.sourceSha"'
        )"
    then
        echo \
            "Could not retrieve the previous build's commit." \
            "Falling back to the head of the target branch."

        prev_commit="origin/${SYSTEM_PULLREQUEST_TARGETBRANCH}"
    fi
elif ! prev_commit="$(
        get_build "${BUILD_SOURCEBRANCH}" \
        | jq -re '.value[0].sourceVersion'
    )"
then
    echo \
        "No previous build was found." \
        "Either the previous build is too old and was deleted" \
        "or the branch was empty before this build." \
        "All images will be built."
    exit 0
fi

# Compare diffs
head="$(git rev-parse HEAD)"
printf '%s\n' "Comparing HEAD (${head}) against ${prev_commit}."

if git diff --quiet "${prev_commit}" -- docker/base.Dockerfile; then
    echo "No changes detected in docker/base.Dockerfile."
    echo "##vso[task.setvariable variable=BASE_CHANGED;isOutput=true]False"
else
    # Always rebuild the venv if the base changes.
    exit 0
fi

if git diff --quiet "${prev_commit}" -- docker/venv.Dockerfile Pipfile*; then
    echo "No changes detected in docker/venv.Dockerfile or the Pipfiles."
    echo "##vso[task.setvariable variable=VENV_CHANGED;isOutput=true]False"
elif master_commit="$(
        get_build "refs/heads/master" \
        | jq -re '.value[0].sourceVersion'
    )" \
    && git diff --quiet "${master_commit}" -- docker/base.Dockerfile
then
    # Though base image hasn't changed, it's still needed to build the venv.
    echo "Can pull base image from Docker Hub; no changes made since master."
    echo "##vso[task.setvariable variable=BASE_PULL;isOutput=true]True"
fi
