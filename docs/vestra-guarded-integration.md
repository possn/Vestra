# Vestra guarded integration

Workflow: `.github/workflows/vestra-guarded-pr-integration.yml`.

## Required repository configuration

1. Add Actions secret `VESTRA_INTEGRATION_TOKEN`: a dedicated fine-grained GitHub token with repository Contents **read/write**, Pull Requests **read/write**, Actions **read**. A default `GITHUB_TOKEN` merge does not trigger normal downstream `push` workflows (including deployment). Without this secret, **do not enable opt-in labels**.
2. Verify repository Actions policy allows `actions/github-script@v7` and that workflow file changes can be run. Require the existing CI checks and protected main in branch rules.
3. Only after this workflow's four checks pass on its own PR, merge the workflow. Apply label `vestra-auto-merge` **one PR at a time** to a reviewed PR. Labeling is an explicit authorization to merge without further human approval.
4. Audit the first merge and downstream publish/production-smoke runs. If these do not trigger, remove the label and disable the workflow.

## Invariants

A labeled PR only merges with the exact latest head SHA if its latest PR-specific Runtime JS, Architecture, Browser E2E workflow attempts have succeeded, including both WebKit shards. The PR must be open and mergeable; its base SHA must equal current `main`, with zero commits behind. Recheck before merge; one merge maximum per invocation. A stale PR must be ported and all four gates rerun; this workflow does not bypass or auto-rebase.

Runs on completion of a trusted workflow, on a schedule and manual dispatch, with no checkout of potentially untrusted PR code. No changes to the quote engine.
