{ pkgs ? import <nixpkgs> {} }:
pkgs.mkShell {
  buildInputs = [ pkgs.chromedriver pkgs.chromium pkgs.cmake pkgs.clang ];
  shellHook = ''
    export LD_LIBRARY_PATH="${pkgs.stdenv.cc.cc.lib}/lib/"
    source .venv/bin/activate
  '';
}
