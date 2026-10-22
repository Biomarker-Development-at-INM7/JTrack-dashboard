import grp
import os


def prepare_log_file(log_filename, group_name="jtrack", mode=0o775):
    if not log_filename:
        return

    log_dir = os.path.dirname(log_filename)

    try:
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
            os.chmod(log_dir, mode)

        with open(log_filename, "a"):
            pass

        os.chmod(log_filename, mode)
    except OSError:
        return

    try:
        gid = grp.getgrnam(group_name).gr_gid
    except KeyError:
        return

    for path in (log_dir, log_filename):
        if not path:
            continue
        try:
            os.chown(path, -1, gid)
        except OSError:
            continue
