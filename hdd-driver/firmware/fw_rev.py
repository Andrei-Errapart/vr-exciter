# PlatformIO pre-build script: stamp the firmware with the git revision and build time.
# The firmware prints them (boot banner, fw= in the S status line), so every bench log
# names the firmware it was taken with. "-dirty" means uncommitted changes in the tree.
import subprocess
import time

Import("env")  # noqa: F821 (provided by PlatformIO/SCons)


def git(*args):
    try:
        return subprocess.run(["git", *args], cwd=env["PROJECT_DIR"], capture_output=True,  # noqa: F821
                              text=True, timeout=10).stdout.strip()
    except Exception:
        return ""


rev = git("describe", "--always", "--dirty", "--abbrev=8") or "unknown"
built = time.strftime("%Y-%m-%dT%H:%M:%S%z")
env.Append(CPPDEFINES=[("FW_REV", env.StringifyMacro(rev)),  # noqa: F821
                       ("FW_BUILT", env.StringifyMacro(built))])
print(f"fw_rev.py: FW_REV={rev} FW_BUILT={built}")
