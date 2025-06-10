{ pkgs ? import <nixpkgs> {} }:
pkgs.mkShell rec {
  buildInputs = [
    pkgs.zlib
    #pkgs.nodejs_22
    #pkgs.nodePackages.npm
  ];
  
  shellHook = ''
    export LD_LIBRARY_PATH="${pkgs.lib.makeLibraryPath buildInputs}:$LD_LIBRARY_PATH"
    export LD_LIBRARY_PATH="${pkgs.stdenv.cc.cc.lib.outPath}/lib:$LD_LIBRARY_PATH"
    source .venv/bin/activate
  '';
}
