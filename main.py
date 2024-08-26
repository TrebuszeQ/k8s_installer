import enum
import os.path
import subprocess
import logging
import socket

from ceph.deployment.drive_selection.matchers import logger


class Distro(enum.Enum):
    REDHAT=1
    DEBIAN=2
    UNKNOWN=3

class InitSystem(enum.Enum):
    CGROUPFS="cgroup"
    SYSTEMD="systemd"
    UNKNOWN="unknown"

class ContainerRuntime(enum.Enum):
    CONTAINERD="containerd"
    CRIO="CRI-O"
    DOCKER="Docker Engine"
    UNKNOWN="unknown"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    logger.info("K8s installer started")
    distro = check_distro()
    if distro == Distro.UNKNOWN:
        app_failure("K8s installer failed at OS distribution check")

    if check_c_library(distro) is False:
        app_failure("K8s installer failed at checking systems C library")

    if not check_k8s_ports():
        app_failure("K8s installer failed at checking systems opened ports")

    init_system: InitSystem = check_init_system()
    if init_system.UNKNOWN:
        app_failure("K8s installation failed at checking init system")

    if not write_text_file("/etc/sysctl.d/k8s.conf", "net.ipv4.ip_forward = 1\r"):
        app_failure("K8s installer failed at writing k8s.conf")
    else:
        result = try_run_command(["sudo", "sysctl", "--system"])
        if result is None:
            app_failure("K8s installer failed at applying sysctl changes")

    if check_container_runtime == ContainerRuntime.UNKNOWN:
        app_failure("K8s installer failed at checking systems container runtime")

    logger.info("K8s installer finished successfully")

def check_c_library(distro: Distro):
    if distro.DEBIAN:
        command = ["dpkg", "-s", "libc6"]
    else:
        command = ["dnf", "info", "glibc"]

    result = try_run_command(command)

    if result is None:
        return False
    else:
        logger.info("C library present")
        return True

def check_k8s_ports():
    ports_success = True
    host = "127.0.0.1"
    ports = [6443, 2379, 2380, 10250, 10259, 10256, 10257]
    for i in range(30000, 32767):
        ports.append(i)

    for port in ports:
        ports_success = check_port(host, port)
        if not ports_success:
            logger.error(f"Port access for {port} failed")
            break

    return ports_success

def try_read_character_file(path):
    logger.info("Reading character file")
    try:
        with open(path, "r") as f:
            content = f.read()
    except FileNotFoundError or PermissionError as e:
        logger.error(f"Reading character file at: {path} failed: {e}")

    return content


def check_init_system():
    init_system: InitSystem = InitSystem.UNKNOWN
    if os.path.exists("/run/systemd/system"):
        init_system = InitSystem.SYSTEMD
    else:
        content = try_read_character_file("/proc/1/cgroup")
        if InitSystem.SYSTEMD.value in content:
            init_system = InitSystem.SYSTEMD
        elif InitSystem.CGROUPFS.value in content:
            init_system = InitSystem.CGROUPFS

        logger.info("Systems init system is ", init_system.name)
    return init_system


def app_failure(msg: str):
    logger.critical(msg)
    exit(1)

def try_run_command(command: list[str]):
    command_str = ""
    for elem in command:
        command_str += " " + elem

    logger.info(f"Running command: {command_str}")

    result = None
    try:
        result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except FileNotFoundError as e:
        logger.error("Failed to run command: %s; exception: %s", command_str, e)
    except PermissionError or subprocess.CalledProcessError or OSError or subprocess.TimeoutExpired as e:
        logger.error("Exception occurred: %s", repr(e))

    return result


def check_port(host, port):
    logger.info("Checking if ports are opened")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1)

        try:
            result = sock.connect((host, port))
            logger.info("Check successful: ", result)
            return True

        except socket.error or ConnectionRefusedError as e:
            logger.error(f"Socket error: {e}")
            sock.settimeout(1)
            return False


def check_distro():
    logger.info("Checking distribution")
    distro = Distro.UNKNOWN
    command = ["apt-get", "--version"]
    result = try_run_command(command)

    if result is not None:
        distro = Distro.DEBIAN
        logger.info("Debian based distribution")
    else:
        command = ["dnf", "--version"]
        result = try_run_command(command)
        logger.info("RedHat based distribution")

        if result is not None:
            distro = Distro.REDHAT
        else:
            logger.info("Failed to execute apt nor dnf")

    return distro


def write_text_file(path, text):
    logger.info(f"Writing text file to: {path}")
    try:
        with open(path, "w",  encoding='utf-8') as file:
            file.write(text)
            logger.info("File written")
            return True

    except FileNotFoundError or PermissionError or IOError or IsADirectoryError as e:
        print(f"Exception occurred: {e}")
        return False


def append_text_file(path, text):
    logger.info(f"Writing text file to: {path}")
    with open(path, "a",  encoding='utf-8') as file:
        file.write(text)
        logger.info("File written")

def check_container_runtime():
    logger.info(f"Checking systems container runtime")

    if os.path.exists("/var/run/containerd"):
        runtime = ContainerRuntime.CONTAINERD
        logger.info("Containerd runtime")
    elif os.path.exists("/var/run/crio"):
        runtime = ContainerRuntime.CRIO
        logger.info("CRI-O runtime")
    elif os.path.exists("/var/run/cri-dockerd.sock"):
        runtime = ContainerRuntime.DOCKER
        logger.info("Docker Engine runtime")
    else:
        runtime = ContainerRuntime.UNKNOWN
        logger.error("Unknown container runtime")

    return runtime.UNKNOWN

def check_container_runtime_settings(runtime: ContainerRuntime, init_system: InitSystem):
    logger.info("Checking if container runtime is compatible with init system")
    if runtime.CONTAINERD:



if __name__ == "__main__":
    main()
