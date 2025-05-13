{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = [
    pkgs.python3
    pkgs.python3Packages.setuptools
    pkgs.streamrip


    pkgs.rustc
    pkgs.cargo
    pkgs.rust-analyzer
    pkgs.pkg-config
    pkgs.openssl
    pkgs.gcc  # or gcc if you prefer
  ];
}
