import enum
import os.path
import subprocess
import logging
import socket


class Distro(enum.Enum):
    REDHAT=1
    DEBIAN=2
    UNKNOWN=3

class InitSystem(enum.Enum):
    CGROUPFS=1
    SYSTEMD=2

logger = logging.getLogger(__name__)


def main():
    logger.info("K8s installer started")

    distro = check_distro()
    if distro == Distro.UNKNOWN:
        logger.info("K8s installer failed at OS distribution check")
        return False

    if not check_k8s_ports():
        logger.info("K8s installer failed at checking ports")
        return False

    if not write_text_file("/etc/sysctl.d/k8s.conf", "net.ipv4.ip_forward = 1\r"):
        logger.info("K8s installer failed at writing k8s.conf")

    try_run_command(["sudo", "sysctl", "--system"])

    logger.info("K8s installer finished successfully")


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

def read_character_file(path):
    logger.info("Reading character file")
    try:
        with open(path, "r") as f:
            content = f.read()
    except FileNotFoundError or PermissionError as e:
        logger.error(f"Reading character file at: {path} failed: {e}")

    return content




def check_init_system():
    if os.path.exists("/run/systemd/system"):
        logger.info("Systems init system is systemd")
    else:
        try:
            with open("/proc/1/cgroup", "r") as f:



def app_failure():
    logger.error("Application failure")
    exit(1)


def try_run_command(command):
    logger.info("Running command")

    command_str = ""
    for elem in command:
        command_str += " " + elem

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
    else:
        command = ["dnf", "--version"]
        result = try_run_command(command)

        if result is not None:
            distro = Distro.REDHAT
        else:
            logger.info("Failed to execute apt and dnf")

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

    logger.info()

if __name__ == "__main__":
    main()
