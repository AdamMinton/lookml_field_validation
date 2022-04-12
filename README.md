# Overview

## Intro

LookML field validator is intended to check for LookML dimension short names in another dimension or measure's parameters (like link, liquid, etc.). This can be helpful for any complex liquid code where new dimensions can be routinely tested for compliance.

## Expected Flow

This will run when any pull request is opened/reopened to test a branch if a branch is compliance with the validation tests specified in validation.json. The action will fail if any errors occur. A markdown file will also be outputted containing the result information.

## Setup

### validation.json

Create a folder in the repo named `lookml_validation`. In this folder you will create a json file named `validation.json`. Review the `validation_sample.json` for the layout of the file.

Checks is any singular field that needs its LookML parameter tested for the inclusion of specific short names.

Validation is similar to how sets are created in Looker. ALL_FIELDS\* will default to all dimensions and then you can remove specific fields by using -view_name.field_name.

### Github Actions

In Github Secrets add the following secrets:

1. CLIENT_ID - API3 Client ID for a service account from Looker
2. CLIENT_SECRET - API3 Client Secret for a service account from Looker

In `.github/workflows` add the following file - `lookml_field_validation.yml`. Replace
`<ADD BASE URL HERE>` with

```
name: CI-LookML Field Validator

on:
  pull_request:
    types: [opened, reopened]

jobs:
  lookml_validation_job:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.8]
    env:
      LOOKERSDK_CLIENT_ID: ${{ secrets.CLIENT_ID }}
      LOOKERSDK_CLIENT_SECRET: ${{ secrets.CLIENT_SECRET }}
      LOOKERSDK_BASE_URL: <ADD BASE URL HERE>

    name: LookML Validation Job
    steps:
      - name: Checkout your LookML
        uses: actions/checkout@v2
        with:
          ref: ${{github.head_ref}}
      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v2
        with:
          python-version: ${{ matrix.python-version }}
      - name: Install Python Dependencies
        run: |
          pip install looker_sdk
          pip install mdutils
      - name: Run LookML Validation Job
        run: |
          python ./.github/workflows/lookml_validation.py --branch ${{github.head_ref}} --validation_file validation.json --location ./lookml_validation/ || echo "ERROR=true" >> $GITHUB_ENV
      - name: Commit changes (e.g., lookml_validation_results.md)
        continue-on-error: true
        run: |
          git config user.name github-actions
          git config user.email github-actions@github.com
          git add -A
          git commit -m "Added LookML Validation Results"
          git push
      - name: Set Action Status
        run: |
          if [ "$ERROR" ]; then
            exit 1
          fi
```

In the same workflow folder include `lookml_validation.py`.

Commit changes to main.
