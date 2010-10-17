# -*- coding: utf-8 -*-
# Copyright (C) 2010 Eric Allen
#
# Author: Eric Allen <eric@hackerengineer.net>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA

# Dripbox: Keep remote copy of directory tree in sync with local tree

import os
import logging
import time

import paramiko
import fsevents
from fsevents import Observer, Stream

SSH_KEY = os.path.join(os.environ['HOME'], ".ssh", "id_rsa")
LOCAL_PATH = os.getcwd()

log = logging.getLogger("dripbox")


def launch(username, host, port, remote_path):
    global remote_root, sftp_client

    remote_root = remote_path
    sftp_client = setup_transport(username, host, port)
    dirs_to_watch = [entry for entry in os.listdir(LOCAL_PATH) if
            os.path.isdir(entry) and not entry.startswith(".")]
    watch_files(dirs_to_watch)


def setup_transport(username, host, port):
    transport = paramiko.Transport((host, port))
    key = paramiko.RSAKey.from_private_key_file(SSH_KEY)
    transport.connect(username=username, pkey=key)
    return paramiko.SFTPClient.from_transport(transport)


def is_temp_file(path):
    if path.endswith(".swp"):
        return True
    if path.endswith("~"):
        return True
    if path.startswith(".#"):
        return True
    return False


def update_file(event):
    global remote_root, sftp_client
    full_path = event.name
    if is_temp_file(full_path):
        return
    # Trying to sync git stuff can put remote repo into a really weird state
    if ".git" in full_path:
        return

    mask = event.mask
    truncated_path = full_path.replace(LOCAL_PATH, "")
    remote_path = remote_root + truncated_path
    if mask & fsevents.IN_DELETE:
        log.info("Deleting %s" % full_path)
        if os.path.isdir(full_path):
            sftp_client.rmdir(remote_path)
        else:
            sftp_client.remove(remote_path)
    else:
        if os.path.isdir(full_path):
            log.info("Creating directory %s" % remote_path)
            try:
                sftp_client.mkdir(remote_path)
            except IOError:
                log.info("Directory already exists")
        else:
            log.info("Uploading %s to %s" % (full_path, remote_path))
            try:
                sftp_client.put(full_path, remote_path)
            except EOFError, e:
                log.warn("Couldn't upload file: %s" % e)
                time.sleep(0.1)
                try:
                    sftp_client.put(full_path, remote_path)
                except EOFError, e:
                    log.error("Failed to upload file: %s" % e)
            except OSError, e:
                log.warn("Couldn't upload file: %s" % e)
                time.sleep(0.1)
                try:
                    sftp_client.put(full_path, remote_path)
                except OSError, e:
                    log.error("Failed to upload file: %s" % e)
    log.info("Done")


def watch_files(paths):
    global observer
    observer = Observer()
    stream = Stream(update_file, file_events=True, *paths)
    observer.schedule(stream)
    log.info("Starting observer")
    observer.daemon = True
    observer.start()
    log.info("Observer started")
