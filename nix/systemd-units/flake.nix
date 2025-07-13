{
  description = "subflake for systemd units";

  inputs = {
    root.url = "../..";
    systemd-nix = {
      url = "github:serokell/systemd-nix";
      # Not quite sure how I can enforce the same `nixpkgs` across subflakes.
    };
  };

  outputs =
    {
      self,
      root,
      ...
    }@inputs:
    let
      eachSystem = root.inputs.nixpkgs.lib.genAttrs (import root.inputs.systems);
      pkgsFor = eachSystem (system: root.inputs.nixpkgs.legacyPackages.${system});
    in
    {
      checks = eachSystem (system: self.packages.${system});

      packages = eachSystem (
        system:
        let
          # https://pyproject-nix.github.io/uv2nix/patterns/cross/index.html
          lib = root.inputs.nixpkgs.lib;
          pkgs = pkgsFor.${system};
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
                ExecStart = "${lib.getExe pkgs.python3} ${../../docs/loggen.py} 100";
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
                ExecStart = "${lib.getExe pkgs.python3} -asdf";
                # --number <number-of-messages>
                # --interval <number of seconds loggen will run>
                # --rate message per second
                RemainAfterExit = true;
              };
            };
        in
        {
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
            ${lib.getExe pkgs.bash} ${../../tests/test_data_generator.sh} generate_list_data "0-isd*"
            ${lib.getExe pkgs.bash} ${../../tests/test_data_generator.sh} generate_unit_data "0-isd-example-unit-01.service"
            ${lib.getExe pkgs.bash} ${../../tests/test_data_generator.sh} generate_unit_data "0-isd-example-unit-02.service"
            ${lib.getExe pkgs.bash} ${../../tests/test_data_generator.sh} generate_unit_data "0-isd-example-unit-03.service"
            ${lib.getExe pkgs.bash} ${../../tests/test_data_generator.sh} generate_unit_data "0-isd-example-unit-04.service"
          '';

          generate-doc-test-data = pkgs.writeScriptBin "generate-doc-test-data" ''
            #!${pkgs.lib.getExe pkgs.bash}

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
    };
}
