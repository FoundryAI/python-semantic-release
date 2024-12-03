from __future__ import annotations

from datetime import timedelta
from itertools import count
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from semantic_release.cli.config import ChangelogOutputFormat

import tests.conftest
import tests.const
import tests.util
from tests.const import (
    DEFAULT_BRANCH_NAME,
    EXAMPLE_HVCS_DOMAIN,
    INITIAL_COMMIT_MESSAGE,
    RepoActionStep,
)

if TYPE_CHECKING:
    from typing import Sequence

    from tests.conftest import (
        GetCachedRepoDataFn,
        GetMd5ForSetOfFilesFn,
        GetStableDateNowFn,
    )
    from tests.fixtures.example_project import ExProjectDir
    from tests.fixtures.git_repo import (
        BuildRepoFromDefinitionFn,
        BuildRepoOrCopyCacheFn,
        BuildSpecificRepoFn,
        BuiltRepoResult,
        CommitConvention,
        ConvertCommitSpecsToCommitDefsFn,
        ConvertCommitSpecToCommitDefFn,
        ExProjectGitRepoFn,
        FormatGitMergeCommitMsgFn,
        GetRepoDefinitionFn,
        RepoActionGitMerge,
        RepoActions,
        RepoActionWriteChangelogsDestFile,
        TomlSerializableTypes,
    )


BETA_BRANCH_NAME = "beta"
DEV_BRANCH_NAME = "dev"
FEAT_BRANCH_1_NAME = "feat/feature-1"
FEAT_BRANCH_2_NAME = "feat/feature-2"
FEAT_BRANCH_3_NAME = "feat/feature-3"
FEAT_BRANCH_4_NAME = "feat/feature-4"
FIX_BRANCH_1_NAME = "fix/patch-1"
FIX_BRANCH_2_NAME = "fix/patch-2"


@pytest.fixture(scope="session")
def deps_files_4_git_flow_repo_w_4_release_channels(
    deps_files_4_example_git_project: list[Path],
) -> list[Path]:
    return [
        *deps_files_4_example_git_project,
        # This file
        Path(__file__).absolute(),
        # because of imports
        Path(tests.const.__file__).absolute(),
        Path(tests.util.__file__).absolute(),
        # because of the fixtures
        Path(tests.conftest.__file__).absolute(),
    ]


@pytest.fixture(scope="session")
def build_spec_hash_4_git_flow_repo_w_4_release_channels(
    get_md5_for_set_of_files: GetMd5ForSetOfFilesFn,
    deps_files_4_git_flow_repo_w_4_release_channels: list[Path],
) -> str:
    # Generates a hash of the build spec to set when to invalidate the cache
    return get_md5_for_set_of_files(deps_files_4_git_flow_repo_w_4_release_channels)


@pytest.fixture(scope="session")
def get_repo_definition_4_git_flow_repo_w_4_release_channels(
    convert_commit_specs_to_commit_defs: ConvertCommitSpecsToCommitDefsFn,
    convert_commit_spec_to_commit_def: ConvertCommitSpecToCommitDefFn,
    format_merge_commit_msg_git: FormatGitMergeCommitMsgFn,
    changelog_md_file: Path,
    changelog_rst_file: Path,
    stable_now_date: GetStableDateNowFn,
) -> GetRepoDefinitionFn:
    """
    This fixture returns a function that when called will define the actions needed to
    build a git repo that uses the git flow branching strategy and git merge commits
    with 4 release channels.

    This very complex repository mirrors the git flow example provided by a user in
    issue [#789](https://github.com/python-semantic-release/python-semantic-release/issues/789).

        1. [feature branches] revision releases which include build-metadata of the branch
            name (slightly differs from user where the release also used alpha+build-metadata)

        2. [dev branch] alpha feature releases (x.x.x-alpha.x)

        3. [beta branch] beta releases (x.x.x-beta.x)

        4. [main branch] official (production) releases (x.x.x)
    """

    def _get_repo_from_defintion(
        commit_type: CommitConvention,
        hvcs_client_name: str = "github",
        hvcs_domain: str = EXAMPLE_HVCS_DOMAIN,
        tag_format_str: str | None = None,
        extra_configs: dict[str, TomlSerializableTypes] | None = None,
        mask_initial_release: bool = False,
    ) -> Sequence[RepoActions]:
        stable_now_datetime = stable_now_date()
        commit_timestamp_gen = (
            (stable_now_datetime + timedelta(seconds=i)).isoformat(timespec="seconds")
            for i in count(step=1)
        )

        # Common static actions or components
        changelog_file_definitons: Sequence[RepoActionWriteChangelogsDestFile] = [
            {
                "path": changelog_md_file,
                "format": ChangelogOutputFormat.MARKDOWN,
            },
            {
                "path": changelog_rst_file,
                "format": ChangelogOutputFormat.RESTRUCTURED_TEXT,
            },
        ]

        fast_forward_dev_branch_actions: Sequence[RepoActions] = [
            {
                "action": RepoActionStep.GIT_CHECKOUT,
                "details": {"branch": DEV_BRANCH_NAME},
            },
            {
                "action": RepoActionStep.GIT_MERGE,
                "details": {
                    "branch_name": BETA_BRANCH_NAME,
                    "fast_forward": True,
                },
            },
        ]

        fast_forward_beta_branch_actions: Sequence[RepoActions] = [
            {
                "action": RepoActionStep.GIT_CHECKOUT,
                "details": {"branch": BETA_BRANCH_NAME},
            },
            {
                "action": RepoActionStep.GIT_MERGE,
                "details": {
                    "branch_name": DEFAULT_BRANCH_NAME,
                    "fast_forward": True,
                },
            },
        ]

        merge_dev_into_beta: RepoActionGitMerge = {
            "action": RepoActionStep.GIT_MERGE,
            "details": {
                "branch_name": DEV_BRANCH_NAME,
                "fast_forward": False,
                "commit_def": convert_commit_spec_to_commit_def(
                    {
                        "angular": format_merge_commit_msg_git(
                            branch_name=DEV_BRANCH_NAME,
                            tgt_branch_name=BETA_BRANCH_NAME,
                        ),
                        "emoji": format_merge_commit_msg_git(
                            branch_name=DEV_BRANCH_NAME,
                            tgt_branch_name=BETA_BRANCH_NAME,
                        ),
                        "scipy": format_merge_commit_msg_git(
                            branch_name=DEV_BRANCH_NAME,
                            tgt_branch_name=BETA_BRANCH_NAME,
                        ),
                        "datetime": next(commit_timestamp_gen),
                        "include_in_changelog": bool(commit_type == "emoji"),
                    },
                    commit_type,
                ),
            },
        }

        merge_beta_into_main: RepoActionGitMerge = {
            "action": RepoActionStep.GIT_MERGE,
            "details": {
                "branch_name": BETA_BRANCH_NAME,
                "fast_forward": False,
                "commit_def": convert_commit_spec_to_commit_def(
                    {
                        "angular": format_merge_commit_msg_git(
                            branch_name=BETA_BRANCH_NAME,
                            tgt_branch_name=DEFAULT_BRANCH_NAME,
                        ),
                        "emoji": format_merge_commit_msg_git(
                            branch_name=BETA_BRANCH_NAME,
                            tgt_branch_name=DEFAULT_BRANCH_NAME,
                        ),
                        "scipy": format_merge_commit_msg_git(
                            branch_name=BETA_BRANCH_NAME,
                            tgt_branch_name=DEFAULT_BRANCH_NAME,
                        ),
                        "datetime": next(commit_timestamp_gen),
                        "include_in_changelog": bool(commit_type == "emoji"),
                    },
                    commit_type,
                ),
            },
        }

        # Define All the steps required to create the repository
        repo_construction_steps: list[RepoActions] = []

        repo_construction_steps.append(
            {
                "action": RepoActionStep.CONFIGURE,
                "details": {
                    "commit_type": commit_type,
                    "hvcs_client_name": hvcs_client_name,
                    "hvcs_domain": hvcs_domain,
                    "tag_format_str": tag_format_str,
                    "mask_initial_release": mask_initial_release,
                    "extra_configs": {
                        # Set the default release branch
                        "tool.semantic_release.branches.main": {
                            "match": rf"^{DEFAULT_BRANCH_NAME}$",
                            "prerelease": False,
                        },
                        # branch "beta" has prerelease suffix of "beta"
                        "tool.semantic_release.branches.beta": {
                            "match": rf"^{BETA_BRANCH_NAME}$",
                            "prerelease": True,
                            "prerelease_token": "beta",
                        },
                        # branch "development" has prerelease suffix of "alpha"
                        "tool.semantic_release.branches.dev": {
                            "match": rf"^{DEV_BRANCH_NAME}$",
                            "prerelease": True,
                            "prerelease_token": "alpha",
                        },
                        # branch "feat/*" has prerelease suffix of "rev"
                        "tool.semantic_release.branches.features": {
                            "match": r"^feat/.+",
                            "prerelease": True,
                            "prerelease_token": "rev",
                        },
                        "tool.semantic_release.allow_zero_version": False,
                        **(extra_configs or {}),
                    },
                },
            }
        )

        # Make initial release
        new_version = "1.0.0"
        repo_construction_steps.extend(
            [
                {
                    "action": RepoActionStep.MAKE_COMMITS,
                    "details": {
                        "commits": [
                            # only one commit to start the main branch
                            convert_commit_spec_to_commit_def(
                                {
                                    "angular": INITIAL_COMMIT_MESSAGE,
                                    "emoji": INITIAL_COMMIT_MESSAGE,
                                    "scipy": INITIAL_COMMIT_MESSAGE,
                                    "datetime": next(commit_timestamp_gen),
                                    "include_in_changelog": bool(
                                        commit_type == "emoji"
                                    ),
                                },
                                commit_type,
                            ),
                        ],
                    },
                },
                {
                    "action": RepoActionStep.GIT_CHECKOUT,
                    "details": {
                        "create_branch": {
                            "name": BETA_BRANCH_NAME,
                            "start_branch": DEFAULT_BRANCH_NAME,
                        },
                    },
                },
                {
                    "action": RepoActionStep.GIT_CHECKOUT,
                    "details": {
                        "create_branch": {
                            "name": DEV_BRANCH_NAME,
                            "start_branch": BETA_BRANCH_NAME,
                        },
                    },
                },
                {
                    "action": RepoActionStep.GIT_CHECKOUT,
                    "details": {
                        "create_branch": {
                            "name": FEAT_BRANCH_1_NAME,
                            "start_branch": DEV_BRANCH_NAME,
                        },
                    },
                },
                {
                    "action": RepoActionStep.MAKE_COMMITS,
                    "details": {
                        "commits": convert_commit_specs_to_commit_defs(
                            [
                                {
                                    "angular": "feat: add new feature",
                                    "emoji": ":sparkles: add new feature",
                                    "scipy": "ENH: add new feature",
                                    "datetime": next(commit_timestamp_gen),
                                    "include_in_changelog": True,
                                },
                            ],
                            commit_type,
                        ),
                    },
                },
                {
                    "action": RepoActionStep.GIT_CHECKOUT,
                    "details": {"branch": DEV_BRANCH_NAME},
                },
                {
                    "action": RepoActionStep.GIT_MERGE,
                    "details": {
                        "branch_name": FEAT_BRANCH_1_NAME,
                        "fast_forward": False,
                        "commit_def": convert_commit_spec_to_commit_def(
                            {
                                "angular": format_merge_commit_msg_git(
                                    branch_name=FEAT_BRANCH_1_NAME,
                                    tgt_branch_name=DEV_BRANCH_NAME,
                                ),
                                "emoji": format_merge_commit_msg_git(
                                    branch_name=FEAT_BRANCH_1_NAME,
                                    tgt_branch_name=DEV_BRANCH_NAME,
                                ),
                                "scipy": format_merge_commit_msg_git(
                                    branch_name=FEAT_BRANCH_1_NAME,
                                    tgt_branch_name=DEV_BRANCH_NAME,
                                ),
                                "datetime": next(commit_timestamp_gen),
                                "include_in_changelog": bool(commit_type == "emoji"),
                            },
                            commit_type,
                        ),
                    },
                },
                {
                    "action": RepoActionStep.GIT_CHECKOUT,
                    "details": {"branch": BETA_BRANCH_NAME},
                },
                {
                    **merge_dev_into_beta,
                },
                {
                    "action": RepoActionStep.GIT_CHECKOUT,
                    "details": {"branch": DEFAULT_BRANCH_NAME},
                },
                {
                    **merge_beta_into_main,
                },
                {
                    "action": RepoActionStep.RELEASE,
                    "details": {
                        "version": new_version,
                        "datetime": next(commit_timestamp_gen),
                        "pre_actions": [
                            {
                                "action": RepoActionStep.WRITE_CHANGELOGS,
                                "details": {
                                    "new_version": new_version,
                                    "dest_files": changelog_file_definitons,
                                },
                            },
                        ],
                    },
                },
            ]
        )

        # Make a fix and release it as an alpha release
        new_version = "1.0.1-alpha.1"
        repo_construction_steps.extend(
            [
                *fast_forward_beta_branch_actions,
                *fast_forward_dev_branch_actions,
                {
                    "action": RepoActionStep.GIT_CHECKOUT,
                    "details": {
                        "create_branch": {
                            "name": FIX_BRANCH_1_NAME,
                            "start_branch": DEV_BRANCH_NAME,
                        }
                    },
                },
                {
                    "action": RepoActionStep.MAKE_COMMITS,
                    "details": {
                        "commits": convert_commit_specs_to_commit_defs(
                            [
                                {
                                    "angular": "fix(cli): fix config cli command",
                                    "emoji": ":bug: (cli) fix config cli command",
                                    "scipy": "BUG(cli): fix config cli command",
                                    "datetime": next(commit_timestamp_gen),
                                    "include_in_changelog": True,
                                },
                            ],
                            commit_type,
                        ),
                    },
                },
                {
                    "action": RepoActionStep.GIT_CHECKOUT,
                    "details": {"branch": DEV_BRANCH_NAME},
                },
                {
                    "action": RepoActionStep.GIT_MERGE,
                    "details": {
                        "branch_name": FIX_BRANCH_1_NAME,
                        "fast_forward": False,
                        "commit_def": convert_commit_spec_to_commit_def(
                            {
                                "angular": format_merge_commit_msg_git(
                                    branch_name=FIX_BRANCH_1_NAME,
                                    tgt_branch_name=DEV_BRANCH_NAME,
                                ),
                                "emoji": format_merge_commit_msg_git(
                                    branch_name=FIX_BRANCH_1_NAME,
                                    tgt_branch_name=DEV_BRANCH_NAME,
                                ),
                                "scipy": format_merge_commit_msg_git(
                                    branch_name=FIX_BRANCH_1_NAME,
                                    tgt_branch_name=DEV_BRANCH_NAME,
                                ),
                                "datetime": next(commit_timestamp_gen),
                                "include_in_changelog": bool(commit_type == "emoji"),
                            },
                            commit_type,
                        ),
                    },
                },
                {
                    "action": RepoActionStep.RELEASE,
                    "details": {
                        "version": new_version,
                        "datetime": next(commit_timestamp_gen),
                        "pre_actions": [
                            {
                                "action": RepoActionStep.WRITE_CHANGELOGS,
                                "details": {
                                    "new_version": new_version,
                                    "dest_files": changelog_file_definitons,
                                },
                            },
                        ],
                    },
                },
            ]
        )

        # Merge in the successful alpha release and create a beta release
        new_version = "1.0.1-beta.1"
        repo_construction_steps.extend(
            [
                {
                    "action": RepoActionStep.GIT_CHECKOUT,
                    "details": {"branch": BETA_BRANCH_NAME},
                },
                {
                    **merge_dev_into_beta,
                },
                {
                    "action": RepoActionStep.RELEASE,
                    "details": {
                        "version": new_version,
                        "datetime": next(commit_timestamp_gen),
                        "pre_actions": [
                            {
                                "action": RepoActionStep.WRITE_CHANGELOGS,
                                "details": {
                                    "new_version": new_version,
                                    "dest_files": changelog_file_definitons,
                                },
                            },
                        ],
                    },
                },
            ]
        )

        # Fix a bug found in beta release and create a new alpha release
        new_version = "1.0.1-alpha.2"
        repo_construction_steps.extend(
            [
                *fast_forward_dev_branch_actions,
                {
                    "action": RepoActionStep.GIT_CHECKOUT,
                    "details": {
                        "create_branch": {
                            "name": FIX_BRANCH_2_NAME,
                            "start_branch": DEV_BRANCH_NAME,
                        }
                    },
                },
                {
                    "action": RepoActionStep.MAKE_COMMITS,
                    "details": {
                        "commits": convert_commit_specs_to_commit_defs(
                            [
                                {
                                    "angular": "fix(config): fix config option",
                                    "emoji": ":bug: (config) fix config option",
                                    "scipy": "BUG(config): fix config option",
                                    "datetime": next(commit_timestamp_gen),
                                    "include_in_changelog": True,
                                },
                            ],
                            commit_type,
                        ),
                    },
                },
                {
                    "action": RepoActionStep.GIT_CHECKOUT,
                    "details": {"branch": DEV_BRANCH_NAME},
                },
                {
                    "action": RepoActionStep.GIT_MERGE,
                    "details": {
                        "branch_name": FIX_BRANCH_2_NAME,
                        "fast_forward": False,
                        "commit_def": convert_commit_spec_to_commit_def(
                            {
                                "angular": format_merge_commit_msg_git(
                                    branch_name=FIX_BRANCH_2_NAME,
                                    tgt_branch_name=DEV_BRANCH_NAME,
                                ),
                                "emoji": format_merge_commit_msg_git(
                                    branch_name=FIX_BRANCH_2_NAME,
                                    tgt_branch_name=DEV_BRANCH_NAME,
                                ),
                                "scipy": format_merge_commit_msg_git(
                                    branch_name=FIX_BRANCH_2_NAME,
                                    tgt_branch_name=DEV_BRANCH_NAME,
                                ),
                                "datetime": next(commit_timestamp_gen),
                                "include_in_changelog": bool(commit_type == "emoji"),
                            },
                            commit_type,
                        ),
                    },
                },
                {
                    "action": RepoActionStep.RELEASE,
                    "details": {
                        "version": new_version,
                        "datetime": next(commit_timestamp_gen),
                        "pre_actions": [
                            {
                                "action": RepoActionStep.WRITE_CHANGELOGS,
                                "details": {
                                    "new_version": new_version,
                                    "dest_files": changelog_file_definitons,
                                },
                            },
                        ],
                    },
                },
            ]
        )

        # Merge in the 2nd successful alpha release and create a secondary beta release
        new_version = "1.0.1-beta.2"
        repo_construction_steps.extend(
            [
                {
                    "action": RepoActionStep.GIT_CHECKOUT,
                    "details": {"branch": BETA_BRANCH_NAME},
                },
                {
                    **merge_dev_into_beta,
                },
                {
                    "action": RepoActionStep.RELEASE,
                    "details": {
                        "version": new_version,
                        "datetime": next(commit_timestamp_gen),
                        "pre_actions": [
                            {
                                "action": RepoActionStep.WRITE_CHANGELOGS,
                                "details": {
                                    "new_version": new_version,
                                    "dest_files": changelog_file_definitons,
                                },
                            },
                        ],
                    },
                },
            ]
        )

        # Add a new feature (another developer was working on) and create a release for it
        new_version = f"1.1.0-rev.1+{FEAT_BRANCH_2_NAME}"
        repo_construction_steps.extend(
            [
                *fast_forward_dev_branch_actions,
                {
                    "action": RepoActionStep.GIT_CHECKOUT,
                    "details": {
                        "create_branch": {
                            "name": FEAT_BRANCH_2_NAME,
                            "start_branch": DEV_BRANCH_NAME,
                        }
                    },
                },
                {
                    "action": RepoActionStep.MAKE_COMMITS,
                    "details": {
                        "commits": convert_commit_specs_to_commit_defs(
                            [
                                {
                                    "angular": "feat(feat-2): add another primary feature",
                                    "emoji": ":sparkles: (feat-2) add another primary feature",
                                    "scipy": "ENH(feat-2): add another primary feature",
                                    "datetime": next(commit_timestamp_gen),
                                    "include_in_changelog": True,
                                },
                            ],
                            commit_type,
                        ),
                    },
                },
                {
                    "action": RepoActionStep.RELEASE,
                    "details": {
                        "version": new_version,
                        "datetime": next(commit_timestamp_gen),
                        "pre_actions": [
                            {
                                "action": RepoActionStep.WRITE_CHANGELOGS,
                                "details": {
                                    "new_version": new_version,
                                    "dest_files": changelog_file_definitons,
                                },
                            },
                        ],
                    },
                },
            ]
        )

        # Merge in the successful revision release and create an alpha release
        new_version = "1.1.0-alpha.1"
        repo_construction_steps.extend(
            [
                {
                    "action": RepoActionStep.GIT_CHECKOUT,
                    "details": {"branch": DEV_BRANCH_NAME},
                },
                {
                    "action": RepoActionStep.GIT_MERGE,
                    "details": {
                        "branch_name": FEAT_BRANCH_2_NAME,
                        "fast_forward": False,
                        "commit_def": convert_commit_spec_to_commit_def(
                            {
                                "angular": format_merge_commit_msg_git(
                                    branch_name=FEAT_BRANCH_2_NAME,
                                    tgt_branch_name=DEV_BRANCH_NAME,
                                ),
                                "emoji": format_merge_commit_msg_git(
                                    branch_name=FEAT_BRANCH_2_NAME,
                                    tgt_branch_name=DEV_BRANCH_NAME,
                                ),
                                "scipy": format_merge_commit_msg_git(
                                    branch_name=FEAT_BRANCH_2_NAME,
                                    tgt_branch_name=DEV_BRANCH_NAME,
                                ),
                                "datetime": next(commit_timestamp_gen),
                                "include_in_changelog": bool(commit_type == "emoji"),
                            },
                            commit_type,
                        ),
                    },
                },
                {
                    "action": RepoActionStep.RELEASE,
                    "details": {
                        "version": new_version,
                        "datetime": next(commit_timestamp_gen),
                        "pre_actions": [
                            {
                                "action": RepoActionStep.WRITE_CHANGELOGS,
                                "details": {
                                    "new_version": new_version,
                                    "dest_files": changelog_file_definitons,
                                },
                            },
                        ],
                    },
                },
            ]
        )

        # Merge in the successful alpha release and create a beta release
        new_version = "1.1.0-beta.1"
        repo_construction_steps.extend(
            [
                {
                    "action": RepoActionStep.GIT_CHECKOUT,
                    "details": {"branch": BETA_BRANCH_NAME},
                },
                {
                    **merge_dev_into_beta,
                },
                {
                    "action": RepoActionStep.RELEASE,
                    "details": {
                        "version": new_version,
                        "datetime": next(commit_timestamp_gen),
                        "pre_actions": [
                            {
                                "action": RepoActionStep.WRITE_CHANGELOGS,
                                "details": {
                                    "new_version": new_version,
                                    "dest_files": changelog_file_definitons,
                                },
                            },
                        ],
                    },
                },
            ]
        )

        # officially release the sucessful release candidate to production
        new_version = "1.1.0"
        repo_construction_steps.extend(
            [
                {
                    "action": RepoActionStep.GIT_CHECKOUT,
                    "details": {"branch": DEFAULT_BRANCH_NAME},
                },
                {
                    **merge_beta_into_main,
                },
                {
                    "action": RepoActionStep.RELEASE,
                    "details": {
                        "version": new_version,
                        "datetime": next(commit_timestamp_gen),
                        "pre_actions": [
                            {
                                "action": RepoActionStep.WRITE_CHANGELOGS,
                                "details": {
                                    "new_version": new_version,
                                    "dest_files": changelog_file_definitons,
                                },
                            },
                        ],
                    },
                },
            ]
        )

        return repo_construction_steps

    return _get_repo_from_defintion


@pytest.fixture(scope="session")
def build_git_flow_repo_w_4_release_channels(
    build_repo_from_definition: BuildRepoFromDefinitionFn,
    get_repo_definition_4_git_flow_repo_w_4_release_channels: GetRepoDefinitionFn,
    get_cached_repo_data: GetCachedRepoDataFn,
    build_repo_or_copy_cache: BuildRepoOrCopyCacheFn,
    build_spec_hash_4_git_flow_repo_w_4_release_channels: str,
) -> BuildSpecificRepoFn:
    def _build_specific_repo_type(
        repo_name: str, commit_type: CommitConvention, dest_dir: Path
    ) -> Sequence[RepoActions]:
        def _build_repo(cached_repo_path: Path) -> Sequence[RepoActions]:
            repo_construction_steps = (
                get_repo_definition_4_git_flow_repo_w_4_release_channels(
                    commit_type=commit_type,
                )
            )
            return build_repo_from_definition(cached_repo_path, repo_construction_steps)

        build_repo_or_copy_cache(
            repo_name=repo_name,
            build_spec_hash=build_spec_hash_4_git_flow_repo_w_4_release_channels,
            build_repo_func=_build_repo,
            dest_dir=dest_dir,
        )

        if not (cached_repo_data := get_cached_repo_data(proj_dirname=repo_name)):
            raise ValueError("Failed to retrieve repo data from cache")

        return cached_repo_data["build_definition"]

    return _build_specific_repo_type


# --------------------------------------------------------------------------- #
# Test-level fixtures that will cache the built directory & set up test case  #
# --------------------------------------------------------------------------- #


@pytest.fixture
def repo_w_git_flow_w_beta_alpha_rev_prereleases_n_angular_commits(
    build_git_flow_repo_w_4_release_channels: BuildSpecificRepoFn,
    example_project_git_repo: ExProjectGitRepoFn,
    example_project_dir: ExProjectDir,
    change_to_ex_proj_dir: None,
) -> BuiltRepoResult:
    repo_name = repo_w_git_flow_w_beta_alpha_rev_prereleases_n_angular_commits.__name__
    commit_type: CommitConvention = repo_name.split("_")[-2]  # type: ignore[assignment]

    return {
        "definition": build_git_flow_repo_w_4_release_channels(
            repo_name=repo_name,
            commit_type=commit_type,
            dest_dir=example_project_dir,
        ),
        "repo": example_project_git_repo(),
    }


@pytest.fixture
def repo_w_git_flow_w_beta_alpha_rev_prereleases_n_emoji_commits(
    build_git_flow_repo_w_4_release_channels: BuildSpecificRepoFn,
    example_project_git_repo: ExProjectGitRepoFn,
    example_project_dir: ExProjectDir,
    change_to_ex_proj_dir: None,
) -> BuiltRepoResult:
    repo_name = repo_w_git_flow_w_beta_alpha_rev_prereleases_n_emoji_commits.__name__
    commit_type: CommitConvention = repo_name.split("_")[-2]  # type: ignore[assignment]

    return {
        "definition": build_git_flow_repo_w_4_release_channels(
            repo_name=repo_name,
            commit_type=commit_type,
            dest_dir=example_project_dir,
        ),
        "repo": example_project_git_repo(),
    }


@pytest.fixture
def repo_w_git_flow_w_beta_alpha_rev_prereleases_n_scipy_commits(
    build_git_flow_repo_w_4_release_channels: BuildSpecificRepoFn,
    example_project_git_repo: ExProjectGitRepoFn,
    example_project_dir: ExProjectDir,
    change_to_ex_proj_dir: None,
) -> BuiltRepoResult:
    repo_name = repo_w_git_flow_w_beta_alpha_rev_prereleases_n_scipy_commits.__name__
    commit_type: CommitConvention = repo_name.split("_")[-2]  # type: ignore[assignment]

    return {
        "definition": build_git_flow_repo_w_4_release_channels(
            repo_name=repo_name,
            commit_type=commit_type,
            dest_dir=example_project_dir,
        ),
        "repo": example_project_git_repo(),
    }