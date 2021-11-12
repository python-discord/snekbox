import sys
from pathlib import Path

import toml

PIPFILE = Path("Pipfile")
DOCKERFILE = Path("Dockerfile")
SNEKBOX_CFG = Path("config/snekbox.cfg")


try:
    # Validate version
    version = str(float(sys.argv[1]))
except ValueError:
    print(f"Could not convert `{sys.argv[1]}` into a valid version number.")
    exit(1)


old_version = toml.load(PIPFILE)["requires"]["python_version"]
print(f"Upgrading from {old_version} to {version}")


print("Upgrading Pipfile")
new_content = PIPFILE.read_text(encoding="utf-8").replace(
    f'python_version = "{old_version}"', f'python_version = "{version}"'
)
PIPFILE.write_text(new_content, encoding="utf-8")


print("Upgrading Dockerfile")
new_content = DOCKERFILE.read_text(encoding="utf-8").replace(f"--branch {old_version}", f"--branch {version}")
DOCKERFILE.write_text(new_content, encoding="utf-8")


print("Upgrade snekbox.cfg")
new_content = SNEKBOX_CFG.read_text(encoding="utf-8").replace(f"lib/python{old_version}", f"lib/python{version}")
SNEKBOX_CFG.write_text(new_content, encoding="utf-8")
