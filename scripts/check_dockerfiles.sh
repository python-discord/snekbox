#!/usr/bin/env bash

REQUEST_URL="https://dev.azure.com/python-discord/${SYSTEM_TEAMPROJECTID}/_apis/build/builds?queryOrder=finishTimeDescending&resultFilter=succeeded&\$top=1&repositoryType=${BUILD_REPOSITORY_PROVIDER}&repositoryId=${BUILD_REPOSITORY_NAME}&branchName=${BUILD_SOURCEBRANCH}&api-version=5.0"
echo "Retrieving previous build's commit using $REQUEST_URL"
RESPONSE="$(curl -sSL "${REQUEST_URL}")"

if [[ $BUILD_REASON = "PullRequest" ]]; then
    PREV_COMMIT="$(echo "${RESPONSE}" | grep -Po '"pr\.sourceSha"\s*:\s*"\K.*?[^\\](?="\s*[,}])')"
    if [[ -z $PREV_COMMIT ]]; then
        echo "Could not retrieve the previous build's commit. Falling back to the head of the target branch."
        PREV_COMMIT="origin/$SYSTEM_PULLREQUEST_TARGETBRANCH"
    fi
else
    PREV_COMMIT="$(echo "${RESPONSE}" | grep -Po '"sourceVersion"\s*:\s*"\K.*?[^\\](?="\s*[,}])')"
fi

if [[ -n $PREV_COMMIT ]]; then
    echo "Using $PREV_COMMIT to compare diffs."

    if [[ -z "$(git diff $PREV_COMMIT -- docker/base.Dockerfile)" ]]; then
        echo "No changes detected in docker/base.Dockerfile. The base image will not be built."
        echo "##vso[task.setvariable variable=BASE_CHANGED]false"
    fi

    if [[ -z "$(git diff $PREV_COMMIT -- docker/venv.Dockerfile Pipfile*)" ]]; then
        echo "No changes detected in docker/venv.Dockerfile or the Pipfiles. The venv image will not be built."
        echo "##vso[task.setvariable variable=VENV_CHANGED]false"
    fi
else
    echo "No previous commit was retrieved. Either the previous build is too old and was deleted or the branch was empty before this build. All images will be built."
fi
