{
  description = "interactive systemd flake";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/release-25.05";
    # nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";

    pyproject-nix = {
      url = "github:pyproject-nix/pyproject.nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    uv2nix = {
      url = "github:pyproject-nix/uv2nix";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    pyproject-build-systems = {
      url = "github:pyproject-nix/build-system-pkgs";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.uv2nix.follows = "uv2nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    # Supports linux x86_64 and aarch64.
    systems.url = "github:nix-systems/default-linux";
  };

  # Disclaimer: Uv2nix is new and experimental.
  # Users are expected to be able to contribute fixes.
  #
  # Note that uv2nix is _not_ using Nixpkgs buildPythonPackage.
  # It's using https://pyproject-nix.github.io/pyproject.nix/build.html

  outputs =
    { self, nixpkgs, ... }@inputs:
    let
      inherit (nixpkgs) lib;

      # Load a uv workspace from a workspace root.
      # Uv2nix treats all uv projects as workspace projects.
      workspace = inputs.uv2nix.lib.workspace.loadWorkspace { workspaceRoot = ./.; };

      # Create package overlay from workspace.
      overlay = workspace.mkPyprojectOverlay {
        # Prefer prebuilt binary wheels as a package source.
        # Sdists are less likely to "just work" because of the metadata missing from uv.lock.
        # Binary wheels are more likely to, but may still require overrides for library dependencies.
        sourcePreference = "wheel"; # or sourcePreference = "sdist";
        # Optionally customise PEP 508 environment
        # environ = {
        #   platform_release = "5.10.65";
        # };
      };

      # Extend generated overlay with build fixups
      #
      # Uv2nix can only work with what it has, and uv.lock is missing essential metadata to perform some builds.
      # This is an additional overlay implementing build fixups.
      # See:
      # - https://pyproject-nix.github.io/uv2nix/FAQ.html
      pyprojectOverrides = _final: _prev: {
        # Implement build fixups here.
      };

      eachSystem = nixpkgs.lib.genAttrs (import inputs.systems);
      pkgsFor = eachSystem (system: nixpkgs.legacyPackages.${system});

      # # This example is only using x86_64-linux
      # pkgs = nixpkgs.legacyPackages.x86_64-linux;

      # # Use Python 3.13 from nixpkgs
      # python = pkgs.python313;

      # Construct package set
      pythonSet311 = (
        pkgs:
        let
          # injecting cairosvg from upstream nixpkgs, as it is currently not
          # supported by the uv2nix_hammer project and is still in the todo list.
          # https://pyproject-nix.github.io/pyproject.nix/builders/hacks.html
          # python = pkgs.python312;
          python = pkgs.python311;
          hacks = pkgs.callPackage inputs.pyproject-nix.build.hacks { };
        in
        # Use base package set from pyproject.nix builders
        (pkgs.callPackage inputs.pyproject-nix.build.packages {
          inherit python;
        }).overrideScope
          (
            lib.composeManyExtensions [
              inputs.pyproject-build-systems.overlays.default
              overlay
              pyprojectOverrides
              (_final: prev: {
                cairosvg = hacks.nixpkgsPrebuilt {
                  from = pkgs.python311Packages.cairosvg;
                  prev = prev.cairosvg;
                };
                cairocffi = hacks.nixpkgsPrebuilt {
                  from = pkgs.python311Packages.cairocffi;
                  prev = prev.cairocffi;
                };
              })
              # (_final: prev: {
              #   pythonPkgsBuildHost = prev.pythonPkgsBuildHost.overrideScope pyprojectOverrides;
              # })
            ]
          )
      );
      pythonSet313 = (
        pkgs:
        let
          # injecting cairosvg from upstream nixpkgs, as it is currently not
          # supported by the uv2nix_hammer project and is still in the todo list.
          # https://pyproject-nix.github.io/pyproject.nix/builders/hacks.html
          # pkgs = pkgsFor.${system};
          # python = pkgs.python312;
          python = pkgs.python313;
          hacks = pkgs.callPackage inputs.pyproject-nix.build.hacks { };
        in
        # Use base package set from pyproject.nix builders
        (pkgs.callPackage inputs.pyproject-nix.build.packages {
          inherit python;
        }).overrideScope
          (
            lib.composeManyExtensions [
              inputs.pyproject-build-systems.overlays.default
              overlay
              pyprojectOverrides
              (_final: prev: {
                cairosvg = hacks.nixpkgsPrebuilt {
                  from = pkgs.python313Packages.cairosvg;
                  prev = prev.cairosvg;
                };
                cairocffi = hacks.nixpkgsPrebuilt {
                  from = pkgs.python313Packages.cairocffi;
                  prev = prev.cairocffi;
                };
              })
            ]
          )
      );
    in
    {
      formatter = eachSystem (system: pkgsFor.${system}.nixfmt-rfc-style);
      checks = eachSystem (
        system:
        {
          # pre-commit-check = inputs.pre-commit-hooks.lib.${system}.run {
          #   src = ./.;
          #   hooks = {
          #     nixfmt-rfc-style.enable = true;
          #     trim-trailing-whitespace.enable = true;
          #   };
          # };
        }
        # { }
        // self.packages.${system}
      );

      # Use the newest python version to build packages
      # -> get the benefit of improvements to CPython for free.
      packages = eachSystem (
        system:
        let
          # https://pyproject-nix.github.io/uv2nix/patterns/cross/index.html
          pkgs = pkgsFor.${system};
          # pkgs = pkgsFor.${system}.pkgsCross.aarch64-multiplatform;
          pythonSet = pythonSet313 pkgs;
          version = (builtins.fromTOML (builtins.readFile ./pyproject.toml)).project.version;
        in
        rec {
          default =
            let
              # Package the virtual environment
              # Enable no optional dependencies for production build.
              venv = pythonSet.mkVirtualEnv "isd-tui-env" workspace.deps.default;
            in
            pkgs.stdenvNoCC.mkDerivation {
              pname = "isd";
              inherit version;
              src = venv;
              meta = {
                mainProgram = "isd";
                license = pkgs.lib.getLicenseFromSpdxId "GPL-3.0-or-later";
              };
              buildPhase = ''
                mkdir -p $out/bin
                ln -s $src/bin/isd $out/bin/
                ln -s $src/share $out/
              '';
            };
          isd = default;
          isd-tui = isd;
          player =
            let
              version = "v3.10.0";
              css = builtins.fetchurl {
                url = "https://github.com/asciinema/asciinema-player/releases/download/${version}/asciinema-player.css";
                sha256 = "sha256:1w9p24jpf1nbsr8jsf20ggpgqbrg5zrgzq0dv9g57wxvaxibrdm6";
              };
              js = builtins.fetchurl {
                url = "https://github.com/asciinema/asciinema-player/releases/download/${version}/asciinema-player.min.js";
                sha256 = "sha256:070563ii4hglg5xjajvf3rb5spsbm0kql92j5xl6jy7ff4pzglwk";
              };
            in
            pkgs.runCommand "combine-player" { } ''
              mkdir -p $out
              cp ${css} $out/asciinema-player.css
              cp ${js} $out/asciinema-player.min.js
            '';

          my_asciinema = pkgs.stdenvNoCC.mkDerivation {
            pname = "my_asciinema";
            version = "1.0.0";
            buildInputs = [ pkgs.makeBinaryWrapper ];
            propagatedBuildInputs = [ pkgs.asciinema_3 ];
            dontUnpack = true;
            installPhase = ''
              mkdir -p $out/bin
              mkdir -p $out/config/asciinema
              cp ${pkgs.asciinema_3}/bin/asciinema $out/bin/my_asciinema
              cat > $out/config/asciinema/config.toml <<EOF
              [recording]
              add_marker_key = "^n"
              EOF
              # Wrap the binary to set XDG_CONFIG_HOME
              wrapProgram $out/bin/my_asciinema --set ASCIINEMA_CONFIG_HOME "$out/config/asciinema"
            '';
          };
        }
      );

      # This example provides two different modes of development:
      # - Impurely using uv to manage virtual environments
      # - Pure development using uv2nix to manage virtual environments
      #
      # Use Python311 (oldest supported Python) for local development and testing.
      devShells = eachSystem (
        system:
        let
          pkgs = pkgsFor.${system};
          pythonSet = pythonSet311 pkgs;
        in
        {
          # It is of course perfectly OK to keep using an impure virtualenv workflow and only use uv2nix to build packages.
          # This devShell simply adds Python and undoes the dependency leakage done by Nixpkgs Python infrastructure.
          # impure = pkgs.mkShell {
          #   packages = [
          #     python
          #     pkgs.uv
          #   ];
          #   shellHook = ''
          #     unset PYTHONPATH
          #     export UV_PYTHON_DOWNLOADS=never
          #   '';
          # };

          # This devShell uses uv2nix to construct a virtual environment purely from Nix, using the same dependency specification as the application.
          # The notable difference is that we also apply another overlay here enabling editable mode ( https://setuptools.pypa.io/en/latest/userguide/development_mode.html ).
          #
          # This means that any changes done to your local files do not require a rebuild.
          default =
            let
              # Create an overlay enabling editable mode for all local dependencies.
              editableOverlay = workspace.mkEditablePyprojectOverlay {
                # Use environment variable
                root = "$REPO_ROOT";
                # Optional: Only enable editable for these packages
                # members = [ "hello-world" ];
              };

              # Override previous set with our overridable overlay.
              editablePythonSet = pythonSet.overrideScope editableOverlay;

              # Build virtual environment, with local packages being editable.
              #
              # Enable all optional dependencies for development.
              virtualenv = editablePythonSet.mkVirtualEnv "isd-tui-env" workspace.deps.all;
            in
            pkgs.mkShell {
              packages = [
                virtualenv
                pkgs.uv
                pkgs.asciinema_3
                self.packages.${system}.my_asciinema

                pkgs.lnav
                pkgs.moar
                # pkgs.nushell
                pkgs.quickemu
                # pkgs.debootstrap
              ];
              shellHook = ''
                # Undo dependency propagation by nixpkgs.
                unset PYTHONPATH

                # Don't create venv using uv
                export UV_NO_SYNC=1

                # Prevent uv from downloading managed Python's
                export UV_PYTHON_DOWNLOADS=never

                export VENV=.venv/

                # Get repository root using git. This is expanded at runtime by the editable `.pth` machinery.
                export REPO_ROOT=$(git rev-parse --show-toplevel)
              '';
            };
          # vms = pkgs.mkShell {
          #   packages = [
          #     pkgs.quickemu
          #   ];
          # };
        }
      );
    };
}
