#!/usr/bin/env bash

set -euo pipefail
shopt -s inherit_errexit
exec 3>&1 # New file descriptor to stdout

BASE_URL="https://dev.azure.com/\
python-discord/${SYSTEM_TEAMPROJECTID}/_apis/build/builds?\
queryOrder=finishTimeDescending&\
resultFilter=succeeded&\
\$top=1&\
repositoryType=${BUILD_REPOSITORY_PROVIDER}&\
repositoryId=${BUILD_REPOSITORY_NAME}&\
api-version=5.0"

declare -A build_cache

get_build() {
    local branch="${1:?"get_build: argument 1 'branch' is unset"}"

    # Attempt to use cached value
    if [[ -v build_cache["${branch}"] ]]; then
        printf '%s\n' "Retrieving build for ${branch} from cache." >&3
        printf '%s' "${build_cache[$branch]}"
        return 0
    fi

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
        # Cache the response
        build_cache["${branch}"]="${response}"
        printf '%s' "${response}"
    fi
}

can_pull() {
    local image="${1:?"can_pull: argument 1 'image' is unset"}"

    local master_commit
    if master_commit="$(
            get_build "refs/heads/master" \
            | jq -re '.value[0].sourceVersion'
        )" \
        && git diff --quiet "${master_commit}" -- "${@:2}"
    then
        printf \
            '%s\n' \
            "Can pull ${image} image from Docker Hub; no changes since master."

        printf '%s\n' "##vso[task.setvariable variable=${image^^}_PULL]True"
    else
        printf \
            '%s\n' \
            "Cannot pull ${image} image from Docker Hub due to detected " \
            "changes; the ${image} image will be built."

        return 1
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
    echo "##vso[task.setvariable variable=BASE_CHANGED]False"
else
    # Always rebuild the venv if the base changes.
    echo "Changes detected in docker/base.Dockerfile; all images will be built."
    exit 0
fi

if git diff --quiet "${prev_commit}" -- docker/venv.Dockerfile Pipfile*; then
    echo "No changes detected in docker/venv.Dockerfile or the Pipfiles."
    echo "##vso[task.setvariable variable=VENV_CHANGED]False"

    if ! can_pull venv docker/venv.Dockerfile Pipfile*; then
        # Venv image can't be pulled so it needs to be built.
        # Therefore, the base image is needed too.
        can_pull base docker/base.Dockerfile || true
    fi
else
    echo \
        "Changes detected in docker/venv.Dockerfile or the Pipfiles;" \
        "the venv image will be built."

    # Though base image hasn't changed, it's still needed to build the venv.
    can_pull base docker/base.Dockerfile || true
fi
