{
  description = "Subflake to build the isd.AppImage";
  inputs = {
    root.url = "../..";
    nix-appimage = {
      # I am not sure why 25.05 fails to build `squashfuse` in `nix-appimage` even if
      # they are identical on release-25.05 and unstable...
      # inputs.nixpkgs.follows = "nixpkgs";
      # TODO: Move to main branch once the `extra-files` branch has been merged!
      # https://github.com/ralismark/nix-appimage/pull/26
      # url = "github:ralismark/nix-appimage";
      url = "github:ralismark/nix-appimage/extra-files";
    };
  };

  outputs =
    {
      self,
      root,
      nix-appimage,
      ...
    }:
    let
      eachSystem = root.inputs.nixpkgs.lib.genAttrs (import root.inputs.systems);
      pkgsFor = eachSystem (system: root.inputs.nixpkgs.legacyPackages.${system});
    in
    {
      checks = eachSystem (system: self.packages.${system});
      packages = eachSystem (
        system:
        let
          pkgs = pkgsFor.${system};
          root_pkgs = root.packages.${system};
        in
        {
          default = nix-appimage.lib.${system}.mkAppImage {
            pname = "isd.${system}";
            program = pkgs.lib.getExe (
              root_pkgs.isd.overrideAttrs (oldAttrs: {
                buildInputs = oldAttrs.buildInputs or [ ] ++ [ pkgs.makeBinaryWrapper ];
                postInstall =
                  oldAttrs.postInstall or ""
                  + ''
                    wrapProgram $out/bin/isd --set SYSTEMD_IGNORE_CHROOT yes
                  '';
              })
            );
          };
        }
      );
    };

}
