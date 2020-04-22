#!/usr/bin/env python3
#
## @file
# manifest_repos_maintenance.py
#
# Copyright (c) 2017- 2020, Intel Corporation. All rights reserved.<BR>
# SPDX-License-Identifier: BSD-2-Clause-Patent
#

import os
import traceback
import shutil

import git
from git import Repo

import edkrepo.config.config_factory as cfg
from edkrepo.common.edkrepo_exception import EdkrepoUncommitedChangesException
from edkrepo.common.progress_handler import GitProgressHandler
import edkrepo.common.workspace_maintenance.humble.manifest_repos_maintenance_humble as humble
from edkrepo.common.workspace_maintenance.workspace_maintenance import generate_name_for_obsolete_backup


def pull_single_manifest_repo(url, branch, local_path, reset_hard=False):
    '''
    Clones or syncs a single global manifest repository as defined in either
    the edkrepo.cfg or the edkrepo_user.cfg
    '''
    # If a relative path is used join to the edkrepo global data directory path
    if not os.path.isabs(local_path):
        local_path = os.path.join(cfg.get_edkrepo_global_data_directory(), local_path)
    # Clone the repository if it does not exist locally
    if not os.path.exists(local_path):
        print(humble.CLONE_SINGLE_MAN_REPO.format(local_path, url))
        repo = Repo.clone_from(url, local_path, progress=GitProgressHandler(), branch=branch)
    # Sync the repository if it exists locally
    else:
        repo = Repo(local_path)
        if url in repo.remotes['origin'].urls:
            if repo.is_dirty(untracked_files=True) and not reset_hard:
                raise EdkrepoUncommitedChangesException(humble.SINGLE_MAN_REPO_DIRTY.format(local_path))
            elif repo.is_dirty(untracked_files=True) and reset_hard:
                repo.git.reset('--hard')
            print(humble.SYNC_SINGLE_MAN_REPO.format(local_path))
            if repo.active_branch.name != branch:
                print(humble.SINGLE_MAN_REPO_NOT_CFG_BRANCH.format(repo.active_branch.name, local_path))
                print(humble.SINGLE_MAN_REPO_CHECKOUT_CFG_BRANCH.format(branch))
                repo.git.checkout(branch)
            repo.remotes.origin.pull()
        # If the URL specified for this manifest repo has moved back up the existing
        # local copy and clone the new repository
        else:
            new_path = generate_name_for_obsolete_backup(local_path)
            new_path = os.path.join(os.path.dirname(local_path), new_path)
            print(humble.SINGLE_MAN_REPO_MOVED.format(new_path))
            shutil.move(local_path, new_path)
            print (humble.CLONE_SINGLE_MAN_REPO.format(local_path, url))
            repo = Repo.clone_from(url, local_path, progress=GitProgressHandler(), branch=branch)

def detect_man_repo_conflicts_duplicates(edkrepo_cfg, edkrepo_user_cfg):
    '''
    Determines whether there is are conflicting or duplicated manifest
    repositories listed in the edkrepo.cfg and the edkrepo_user.cfg.
    '''
    conflicts = []
    duplicates = []
    if not edkrepo_user_cfg.manifest_repo_list:
        return conflicts, duplicates
    else:
        config_repos = set(edkrepo_cfg.manifest_repo_list)
        user_cfg_repos = set(edkrepo_user_cfg.manifest_repo_list)
    if config_repos.isdisjoint(user_cfg_repos):
        return conflicts, duplicates
    else:
        for repo in config_repos.intersection(user_cfg_repos):
            if edkrepo_cfg.get_manifest_repo_url(repo) != edkrepo_user_cfg.get_manifest_repo_url(repo):
                conflicts.append(repo)
            elif edkrepo_cfg.get_manifest_repo_branch(repo) != edkrepo_user_cfg.get_manifest_repo_branch(repo):
                conflicts.append(repo)
            elif edkrepo_cfg.get_manifest_repo_local_path(repo) != edkrepo_user_cfg.get_manifest_repo_local_path(repo):
                conflicts.append(repo)
            else:
                duplicates.append(repo)
    return conflicts, duplicates