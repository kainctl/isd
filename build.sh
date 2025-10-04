set -euo pipefail

grep "current_version =" "$REPO_ROOT/pyproject.toml" 

while true; do
  read -rp "Is the current version flag correctly set? [y/N] " yn
  case $yn in
    [yY]* ) break;;
    [Nn]* ) exit;;
    * ) exit ;;
  esac
done

# update the caches
uv sync
touch "$REPO_ROOT/flake.nix"

# ensure that everything works as expected
mkdocs build --clean
pytest "$REPO_ROOT/tests/"

rm -rf "$REPO_ROOT/dist"
rm -f "$REPO_ROOT/isd.x86_64-linux.AppImage"
rm -f "$REPO_ROOT/isd.aarch64-linux.AppImage"

# start building everything
uv build

if [[ -n "$(git status --porcelain | grep '??')" ]]; then
  echo "Untracked files exist"
  exit 1
else
  echo "No untracked files"
fi

rm -rf ./result
echo "Building x86-64 isd-AppImage"
nix build ./?dir=nix/appimage#packages.x86_64-linux.default
cp "$(readlink -f ./result)" isd.x86_64-linux.AppImage

rm -rf ./result
echo "Building aarch64 isd-AppImage"
nix build ./?dir=nix/appimage#packages.aarch64-linux.default
cp "$(readlink -f ./result)" isd.aarch64-linux.AppImage

# publish latest docs
echo "Publishing docs"
mkdocs gh-deploy --no-history

echo "Remember to update PyPI!"

