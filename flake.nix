{
  description = "interactive systemd flake";

  inputs = {
    # 24.11 does _not_ contain asciinema_3
    # nixpkgs.url = "github:NixOS/nixpkgs/release-24.11";
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

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
    nix-filter.url = "github:numtide/nix-filter";
    # pre-commit-hooks.url = "github:cachix/pre-commit-hooks.nix";
    systemd-nix = {
      url = "github:serokell/systemd-nix";
      inputs.nixpkgs.follows = "nixpkgs"; # Make sure the nixpkgs version matches
    };
    nix-appimage = {
      url = "github:ralismark/nix-appimage";
      # nix-appimage cannot track nixos-unstable until this issue is resolved:
      # - <https://github.com/ralismark/nix-appimage/issues/23>
      # inputs.nixpkgs.follows = "nixpkgs";
    };
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
      pythonSet311For = eachSystem (
        system:
        let
          # injecting cairosvg from upstream nixpkgs, as it is currently not
          # supported by the uv2nix_hammer project and is still in the todo list.
          # https://pyproject-nix.github.io/pyproject.nix/builders/hacks.html
          pkgs = pkgsFor.${system};
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
            ]
          )
      );
      pythonSet313For = eachSystem (
        system:
        let
          # injecting cairosvg from upstream nixpkgs, as it is currently not
          # supported by the uv2nix_hammer project and is still in the todo list.
          # https://pyproject-nix.github.io/pyproject.nix/builders/hacks.html
          pkgs = pkgsFor.${system};
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
          pkgs = pkgsFor.${system};
          pythonSet = pythonSet313For.${system};
          version = (builtins.fromTOML (builtins.readFile ./pyproject.toml)).project.version;
          gen_unit =
            name:
            inputs.systemd-nix.lib.${system}.mkUserService name {
              description = name;
              documentation = [ "man:python" ];
              wants = [ "default.target" ];
              after = [ "default.target" ];
              serviceConfig = {
                Type = "simple"; # or oneshot for multiple ExecStart
                # ExecStart = "${lib.getExe' pkgs.coreutils "sleep"} 1m";
                ExecStart = "${lib.getExe pythonSet.python} ${./docs/loggen.py} 100";
                # --number <number-of-messages>
                # --interval <number of seconds loggen will run>
                # --rate message per second
                RemainAfterExit = true;
              };
            };
          gen_broken_unit =
            name:
            inputs.systemd-nix.lib.${system}.mkUserService name {
              description = name;
              documentation = [ "man:python" ];
              wants = [ "default.target" ];
              after = [ "default.target" ];
              serviceConfig = {
                Type = "simple"; # or oneshot for multiple ExecStart
                # ExecStart = "${lib.getExe' pkgs.coreutils "sleep"} 1m";
                ExecStart = "${lib.getExe pythonSet.python} -asdf";
                # --number <number-of-messages>
                # --interval <number of seconds loggen will run>
                # --rate message per second
                RemainAfterExit = true;
              };
            };
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
          "isd-AppImage" = inputs.nix-appimage.lib.${system}.mkAppImage {
            pname = "isd.${system}";
            program = pkgs.lib.getExe (
              isd.overrideAttrs (oldAttrs: {
                buildInputs = oldAttrs.buildInputs or [ ] ++ [ pkgs.makeBinaryWrapper ];
                postInstall =
                  oldAttrs.postInstall or ""
                  + ''
                    wrapProgram $out/bin/isd --set SYSTEMD_IGNORE_CHROOT yes
                  '';
              })
            );
          };
          player =
            let
              version = "v3.8.2";
              css = builtins.fetchurl {
                url = "https://github.com/asciinema/asciinema-player/releases/download/${version}/asciinema-player.css";
                sha256 = "sha256:19jl4ps46cmn31lxccvmza9igpqv66hpg60kd4rc9mp0a677nfsc";
              };
              js = builtins.fetchurl {
                url = "https://github.com/asciinema/asciinema-player/releases/download/${version}/asciinema-player.min.js";
                sha256 = "sha256:1ganjf704k6hm2pvjxyx7jnppvjyhak16m50wxrfbig61gvri8i2";
              };
            in
            pkgs.runCommand "combine-player" { } ''
              mkdir -p $out
              cp ${css} $out/asciinema-player.css
              cp ${js} $out/asciinema-player.min.js
            '';
          isd-example-templated-unit =
            inputs.systemd-nix.lib.${system}.mkUserService "0-isd-example-unit-template@"
              {
                description = "isd-example instantiated unit %i";
                documentation = [ "man:python" ];
                serviceConfig = {
                  Type = "oneshot";
                  ExecStart = "${lib.getExe' pkgs.coreutils "echo"} 'I am unit %i'";
                  RemainAfterExit = true;
                };
              };

          generate-integration-test-data = pkgs.writeScriptBin "generate-integration-test-data" ''
            set -e
            ${lib.getExe (gen_unit "0-isd-example-unit-01")}
            ${lib.getExe (gen_unit "0-isd-example-unit-02")}
            ${lib.getExe (gen_unit "0-isd-example-unit-03")}
            ${lib.getExe (gen_broken_unit "0-isd-example-unit-04")}

            systemctl --user stop "0-isd-example-unit-02.service"
            systemctl --user stop "0-isd-example-unit-03.service"
            ln -s /tmp/__wrong_path_that_does_not_exist --force "$HOME/.config/systemd/user/0-isd-example-unit-03.service"
            # 4 is broken by default
            systemctl --user daemon-reload

            # Now generate the sample data from the above generated state.
            export _SYSTEMD_USER_MODE=1
            export OUT_DIR="$(git rev-parse --show-toplevel)/tests/integration-test/"
            ${lib.getExe pkgs.bash} ${./tests/test_data_generator.sh} generate_list_data "0-isd*"
            ${lib.getExe pkgs.bash} ${./tests/test_data_generator.sh} generate_unit_data "0-isd-example-unit-01.service"
            ${lib.getExe pkgs.bash} ${./tests/test_data_generator.sh} generate_unit_data "0-isd-example-unit-02.service"
            ${lib.getExe pkgs.bash} ${./tests/test_data_generator.sh} generate_unit_data "0-isd-example-unit-03.service"
            ${lib.getExe pkgs.bash} ${./tests/test_data_generator.sh} generate_unit_data "0-isd-example-unit-04.service"
          '';

          generate-doc-test-data = pkgs.writeScriptBin "generate-doc-test-data" ''
            set -e
            ${lib.getExe (gen_unit "0-isd-example-unit-01")}
            ${lib.getExe (gen_unit "0-isd-example-unit-02")}
            ${lib.getExe (gen_unit "0-isd-example-unit-03")}
            ${lib.getExe (gen_broken_unit "0-isd-example-unit-04")}
            ${lib.getExe (gen_unit "0-isd-example-unit-05")}
            ${lib.getExe (gen_unit "0-isd-example-unit-06")}
            ${lib.getExe (gen_unit "0-isd-example-unit-07")}

            systemctl --user stop "0-isd-example-unit-02.service"
            systemctl --user stop "0-isd-example-unit-03.service"
            ln -s /tmp/__wrong_path_that_does_not_exist --force "$HOME/.config/systemd/user/0-isd-example-unit-03.service"
            # 4 is broken by default
            systemctl --user daemon-reload
          '';
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
          pythonSet = pythonSet311For.${system};
          lib = pkgs.lib;
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
