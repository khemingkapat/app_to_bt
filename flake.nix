{
  description = "App to Blue Table - Automatic PDF Form to Tabular Format";
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
  };
  outputs =
    { self, nixpkgs }:
    let
      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system};

      # Define commands as binary scripts so they persist in zsh
      clean-json = pkgs.writeShellScriptBin "clean-json" ''
        if [ -d "outputs" ]; then
          echo "Cleaning JSON files in outputs/ (excluding *.example.json)..."
          find outputs/ -type f -name "*.json" ! -name "*.example.*" -delete
          echo "Done!"
        else
          echo "Directory 'outputs/' does not exist."
        fi
      '';

      setup-json = pkgs.writeShellScriptBin "setup-json" ''
        if [ -d "outputs" ]; then
          echo "Copying .example.json files to .json..."
          for file in outputs/*.example.json; do
            [ -e "$file" ] || continue
            
            # Create the new filename by removing '.example'
            new_file="''${file/.example./.}"

            cp "$file" "$new_file"
            echo "Copied: $file -> $new_file"
          done
          echo "Done!"
        else
          echo "Directory 'outputs/' does not exist."
        fi
      '';

    in
    {
      devShells.${system}.default = pkgs.mkShell {
        buildInputs = with pkgs; [
          go
          protobuf
          protoc-gen-go
          protoc-gen-go-grpc
          nodejs_22
          uv
          python311
          # System libraries needed by pre-compiled Python wheels
          stdenv.cc.cc.lib
          zlib
          # Include your custom binary scripts here
          clean-json
          setup-json
        ];

        env = {
          LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath [
            pkgs.stdenv.cc.cc.lib
            pkgs.zlib
          ];
        };

        shellHook = ''
          echo "🚀 Automation of Application form to Blue Table"
          echo "Run 'uv sync' to install dependencies"
          echo "Run 'uv run jupyter lab' to start"
          echo ""
          echo "✅ Available commands loaded:"
          echo "  clean-json - Clear target JSON files in outputs/"
          echo "  setup-json - Copy *.example.json files to *.json"

          export SHELL=/home/khemi/.nix-profile/bin/zsh
          exec /home/khemi/.nix-profile/bin/zsh
        '';
      };
    };
}
