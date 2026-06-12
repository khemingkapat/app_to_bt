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

      # Script 1: Clean up non-example JSON files
      clean-outputs = pkgs.writeScriptBin "clean-outputs" ''
        #!/usr/bin/env bash
        if [ -d "outputs" ]; then
          echo "Cleaning JSON files in outputs/ (excluding *.example.json)..."
          find outputs/ -type f -name "*.json" ! -name "*.example.*" -delete
          echo "Done!"
        else
          echo "Directory 'outputs/' does not exist."
        fi
      '';

      # Script 2: Copy .example.json files to .json files
      setup-examples = pkgs.writeScriptBin "setup-examples" ''
        #!/usr/bin/env bash
        if [ -d "outputs" ]; then
          echo "Copying .example.json files to .json..."
          for file in outputs/*.example.json; do
            # Check if any matching files actually exist
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
          uv
          python311

          # Added system libraries needed by pre-compiled Python wheels (Jupyter, Pandas, etc.)
          stdenv.cc.cc.lib
          zlib

          # Include both custom scripts
          clean-outputs
          setup-examples
        ];

        # Tell the environment exactly where to find those libraries
        env = {
          LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath [
            pkgs.stdenv.cc.cc.lib
            pkgs.zlib
          ];
        };

        shellHook = ''
          echo "Automation of Application form to Blue Table"
          echo "Run 'uv sync' to install dependencies"
          echo "Run 'uv run jupyter lab' to start"

          # Set up aliases for quick access
          alias clean-json="clean-outputs"
          alias setup-json="setup-examples"

          echo ""
          echo "Available commands:"
          echo "  clean-json - Clear target JSON files in outputs/"
          echo "  setup-json - Copy *.example.json files to *.json"
        '';
      };
    };
}
