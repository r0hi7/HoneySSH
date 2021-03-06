#!/usr/bin/env python

# Copyright (c) 2015 Robert Putt (http://www.github.com/robputt796)
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
# 3. The names of the author(s) may not be used to endorse or promote
#    products derived from this software without specific prior written
#    permission.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHORS ``AS IS'' AND ANY EXPRESS OR
# IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
# OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
# IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
# AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.
import os

from docker import Client
from twisted.python import filepath
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from honssh import spoof, log
from honssh.config import Config
from honssh.honeypot.docker_utils import docker_cleanup
from honssh.utils import validation


class Plugin(object):
    def __init__(self):
        self.cfg = Config.getInstance()
        self.connection_timeout = self.cfg.getint(['honeypot', 'connection_timeout'])
        self.docker_drive = None
        self.container = None
        self.sensor_name = None
        self.peer_ip = None
        self.channel_open = False

    def get_pre_auth_details(self, conn_details):
        return self.get_connection_details(conn_details)

    def get_post_auth_details(self, conn_details):
        success, username, password = spoof.get_connection_details(conn_details)
        if success:
            if self.container is None:
                details = self.get_connection_details(conn_details)
            else:
                details = conn_details
                details['success'] = True

            details['username'] = username
            details['password'] = password
            details['connection_timeout'] = self.connection_timeout
        else:
            details = {'success': False}

        return details

    def get_connection_details(self, conn_details):
        self.peer_ip = conn_details['peer_ip']

        socket = self.cfg.get(['honeypot-docker', 'uri'])
        image = self.cfg.get(['honeypot-docker', 'image'])
        launch_cmd = self.cfg.get(['honeypot-docker', 'launch_cmd'])
        self.sensor_name = self.cfg.get(['honeypot-docker', 'hostname'])
        honey_port = self.cfg.getint(['honeypot-docker', 'honey_port'])
        pids_limit = self.cfg.getint(['honeypot-docker', 'pids_limit'])
        mem_limit = self.cfg.get(['honeypot-docker', 'mem_limit'])
        memswap_limit = self.cfg.get(['honeypot-docker', 'memswap_limit'])
        shm_size = self.cfg.get(['honeypot-docker', 'shm_size'])
        cpu_period = self.cfg.getint(['honeypot-docker', 'cpu_period'])
        cpu_shares = self.cfg.getint(['honeypot-docker', 'cpu_shares'])
        cpuset_cpus = self.cfg.get(['honeypot-docker', 'cpuset_cpus'])
        reuse_container = self.cfg.get(['honeypot-docker', 'reuse_container'])

        self.docker_drive = DockerDriver(socket, image, launch_cmd, self.sensor_name, pids_limit, mem_limit, memswap_limit,
                                         shm_size, cpu_period, cpu_shares, cpuset_cpus, self.peer_ip, reuse_container)
        self.container = self.docker_drive.launch_container()

        honey_ip = self.container['ip']

        return {'success': True, 'sensor_name': self.sensor_name, 'honey_ip': honey_ip, 'honey_port': honey_port,
                'connection_timeout': self.connection_timeout}

    def login_successful(self):
        self.channel_open = True

        '''
        FIXME: Currently output_handler and this plugin do both construct the session folder path. This should be encapsulated.
        '''
        overlay_folder = self.cfg.get(['honeypot-docker', 'overlay_folder'])
        max_filesize = self.cfg.getint(['honeypot-docker', 'overlay_max_filesize'], 51200)
        use_revisions = self.cfg.getboolean(['honeypot-docker', 'overlay_use_revisions'])

        if self.docker_drive.watcher is None and len(overlay_folder) > 0:
            overlay_folder = '%s/%s/%s/%s' % \
                             (self.cfg.get(['folders', 'session_path']),
                              self.sensor_name,
                              self.peer_ip,
                              overlay_folder)

            self.docker_drive.start_watcher(overlay_folder, max_filesize, use_revisions)

    def connection_lost(self, conn_details):
        self.docker_drive.teardown_container(not self.channel_open)

    def start_server(self):
        if self.cfg.getboolean(['honeypot-docker', 'enabled']) and self.cfg.getboolean(['honeypot-docker', 'reuse_container']):
            ttl_prop = ['honeypot-docker', 'reuse_ttl']
            ttl = self.cfg.get(ttl_prop)
            interval_prop = ['honeypot-docker', 'reuse_ttl_check_interval']
            interval = self.cfg.get(interval_prop)

            ttl_valid = False
            interval_valid = False

            if len(ttl) > 0:
                ttl_valid = validation.check_valid_number(ttl_prop, ttl)

            if len(interval) > 0:
                interval_valid = validation.check_valid_number(interval_prop, interval)

            if ttl_valid and interval_valid:
                docker_cleanup.start_cleanup_loop(int(ttl), int(interval))
            elif ttl_valid:
                docker_cleanup.start_cleanup_loop(ttl=int(ttl))
            elif interval_valid:
                docker_cleanup.start_cleanup_loop(interval=int(interval))
            else:
                docker_cleanup.start_cleanup_loop()
        return None

    def validate_config(self):
        props = [['honeypot-docker', 'enabled'], ['honeypot-docker', 'pre-auth'], ['honeypot-docker', 'post-auth'],
                 ['honeypot-docker', 'reuse_container'], ['honeypot-docker', 'overlay_use_revisions']]
        for prop in props:
            if not self.cfg.check_exist(prop, validation.check_valid_boolean):
                return False

        props = [['honeypot-docker', 'image'], ['honeypot-docker', 'uri'], ['honeypot-docker', 'hostname'],
                 ['honeypot-docker', 'launch_cmd'], ['honeypot-docker', 'honey_port']]
        for prop in props:
            if not self.cfg.check_exist(prop):
                return False

        return True


class DockerDriver(object):

    def __init__(self, socket, image, launch_cmd, hostname, pids_limit, mem_limit, memswap_limit, shm_size, cpu_period,
                 cpu_shares, cpuset_cpus, peer_ip, reuse_container):
        self.container_id = None
        self.container_ip = None
        self.connection = None
        self.socket = socket
        self.image = image
        self.hostname = hostname
        self.launch_cmd = launch_cmd
        self.pids_limit = pids_limit
        self.mem_limit = mem_limit
        self.memswap_limit = memswap_limit
        self.shm_size = shm_size
        self.cpu_period = cpu_period
        self.cpu_shares = cpu_shares
        self.cpuset_cpus = cpuset_cpus
        self.peer_ip = peer_ip
        self.reuse_container = reuse_container

        self.watcher = None
        self.overlay_folder = None
        self.mount_dir = None
        self.max_filesize = 0
        self.use_revisions = False

        self.make_connection()

    def make_connection(self):
        self.connection = Client(self.socket)

    def launch_container(self):
        if self.reuse_container:
            try:
                # Check for existing container
                container_data = self.connection.inspect_container(self.peer_ip)
                # Get container id
                self.container_id = container_data['Id']
                log.msg(log.LGREEN, '[PLUGIN][DOCKER]', 'Reusing container %s ' % self.container_id)
                # Restart container
                self.connection.restart(self.container_id)
            except:
                self.container_id = None
                pass

        if self.container_id is None:
            host_config = self.connection.create_host_config(pids_limit=self.pids_limit, mem_limit=self.mem_limit,
                                                             memswap_limit=self.memswap_limit, shm_size=self.shm_size,
                                                             cpu_period=self.cpu_period, cpu_shares=self.cpu_shares,
                                                             cpuset_cpus=self.cpuset_cpus)
            self.container_id = \
                self.connection.create_container(image=self.image, tty=True, hostname=self.hostname,
                                                 name=self.peer_ip, host_config=host_config)['Id']
            self.connection.start(self.container_id)

        exec_id = self.connection.exec_create(self.container_id, self.launch_cmd)['Id']
        self.connection.exec_start(exec_id, tty=True)
        container_data = self.connection.inspect_container(self.container_id)
        self.container_ip = container_data['NetworkSettings']['Networks']['bridge']['IPAddress']

        log.msg(log.LCYAN, '[PLUGIN][DOCKER]',
                'Launched container (%s, %s)' % (self.container_ip, self.container_id))

        return {"id": self.container_id, "ip": self.container_ip}

    def teardown_container(self, destroy_container):
        if self.watcher is not None:
            self.watcher.unschedule_all()
            log.msg(log.LCYAN, '[PLUGIN][DOCKER]', 'Filesystem watcher stopped')

        self.connection.stop(self.container_id)
        log.msg(log.LCYAN, '[PLUGIN][DOCKER]',
                'Stopped container (%s, %s)' % (self.container_ip, self.container_id))

        # Check for container reuse
        if not self.reuse_container or destroy_container:
            self.connection.remove_container(self.container_id, force=True)
            log.msg(log.LCYAN, '[PLUGIN][DOCKER]',
                    'Destroyed container (%s, %s)' % (self.container_ip, self.container_id))

    def _file_get_contents(self, filename):
        with open(filename) as f:
            return f.read()

    def start_watcher(self, dest_path, max_filesize, use_revisions):
        if self.watcher is None:
            self.overlay_folder = dest_path
            self.max_filesize = max_filesize
            self.use_revisions = use_revisions

            # Check if watching should be started
            if len(self.overlay_folder) > 0:
                # Create overlay folder if needed
                if not os.path.exists(self.overlay_folder):
                    os.makedirs(self.overlay_folder)
                    os.chmod(self.overlay_folder, 0755)

                self._start_inotify()

    def _start_inotify(self):
        docker_info = self.connection.info()
        docker_root = docker_info['DockerRootDir']
        storage_driver = docker_info['Driver']

        supported_storage = {
            'aufs': '%s/%s/mnt/%s',  # -> /var/lib/docker/aufs/mnt/<mount-id>
            'btrfs': '%s/%s/subvolumes/%s',  # -> /var/lib/docker/btrfs/subvolumes/<mount-id>
            'overlay': '%s/%s/%s/merged',  # -> /var/lib/docker/overlay/<mount-id>/merged
            'overlay2': '%s/%s/%s/merged'  # -> /var/lib/docker/overlay2/<mount-id>/merged
        }

        if storage_driver in supported_storage:
            # Get container mount id
            mount_id = self._file_get_contents(('%s/image/%s/layerdb/mounts/%s/mount-id' % (docker_root, storage_driver, self.container_id)))
            # construct mount path
            self.mount_dir = supported_storage[storage_driver] % (docker_root, storage_driver, mount_id)

            log.msg(log.LGREEN, '[PLUGIN][DOCKER]', 'Starting filesystem watcher at %s' % self.mount_dir)

            try:
                # Create watcher and start watching
                self.watcher = Observer()
                event_handler = DockerFileSystemEventHandler(self.overlay_folder, self.mount_dir,
                                                             self.max_filesize, self.use_revisions);
                self.watcher.schedule(event_handler, self.mount_dir, recursive=True)
                self.watcher.start()

                log.msg(log.LGREEN, '[PLUGIN][DOCKER]', 'Filesystem watcher started')
            except Exception as exc:
                log.msg(log.LRED, '[PLUGIN][DOCKER]', 'Failed to start filesystem watcher "%s"' % str(exc))
        else:
            log.msg(log.LRED, '[PLUGIN][DOCKER]',
                    'Filesystem watcher not supported for storage driver "%s"' % storage_driver)


class DockerFileSystemEventHandler(FileSystemEventHandler):
    def __init__(self, overlay_folder, mount_dir, max_filesize, use_revisions):
        super(FileSystemEventHandler, self).__init__()
        self.overlay_folder = overlay_folder
        self.mount_dir = mount_dir
        self.max_filesize = max_filesize
        self.use_revisions = use_revisions

    def on_modified(self, event):
        #log.msg(log.LYELLOW, '[FS_WATCH][on_modified]', '%s' % repr(event))

        if not event.is_directory:
            self.process_event(event.src_path)

    def on_moved(self, event):
        #log.msg(log.LYELLOW, '[FS_WATCH][on_moved]', '%s' % repr(event))

        if not event.is_directory:
            self.process_event(event.dest_path)

    def process_event(self, file_path):
        file = filepath.FilePath(file_path)
        #log.msg(log.LYELLOW, '[FS_WATCH][process_event]', '%s' % str(file))

        if file.exists() and file.getsize() > 0:
            # Check max_filesize constraint
            if self.max_filesize == 0 or (self.max_filesize > 0 and (file.getsize() / 1024) <= self.max_filesize):
                # Construct src and dest path as string
                src_path = '%s/%s' % (file.dirname(), file.basename())
                dest_path = '%s/%s' % (self.overlay_folder, src_path.replace(self.mount_dir, ''))

                # Create dest file object
                d = filepath.FilePath(dest_path)

                # Check for revision constraint
                if self.use_revisions and d.exists():
                    c = 0
                    while True:
                        # Increment counter and construct new path
                        c += 1
                        dpath = dest_path + "-" + str(c)
                        d = filepath.FilePath(dpath)

                        # Check for new path
                        if not d.exists():
                            dest_path = dpath
                            break

                #log.msg(log.LBLUE, '[COPY]', '%s / %s' % (src_path, dest_path))

                try:
                    # Create directory tree
                    os.makedirs('%s%s' % (self.overlay_folder, file.dirname().replace(self.mount_dir, '')))
                except:
                    # Ignore exception
                    pass

                try:
                    # Do actual copy
                    file.copyTo(d)
                except Exception as exc:
                    log.msg(log.LRED, '[PLUGIN][DOCKER][FS_WATCH]', 'FAILED TO COPY "%s" - %s' % (src_path, str(exc)))