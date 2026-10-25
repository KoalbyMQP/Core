{
  description = "ZaraOS Core: ROS 2 Humble + Python development shell";

  inputs = {
    nix-ros-overlay.url = "github:lopsided98/nix-ros-overlay/master";
    nixpkgs.follows = "nix-ros-overlay/nixpkgs";
    ros-deps = {
      url = "github:AndrewSuyer/ros-deps";
      inputs.nix-ros-overlay.follows = "nix-ros-overlay";
    };
  };

  outputs = { self, nixpkgs, nix-ros-overlay, ros-deps }:
    # nix-ros-overlay only supports Linux; aarch64 matches the robot target.
    nix-ros-overlay.inputs.flake-utils.lib.eachDefaultSystem (system:
      let
        # setuptools >= 80 turns `requires-python` from pyproject.toml into a
        # SpecifierSet object, whose repr colcon can't parse back, so colcon
        # fails on any ament_python package that has a pyproject.toml
        # (face_ui, poc-demo, python-example). Stringify it before repr().
        colconFix = final: prev: {
          pythonPackagesExtensions = prev.pythonPackagesExtensions ++ [
            (pyFinal: pyPrev: {
              colcon-python-setup-py = pyPrev.colcon-python-setup-py.overridePythonAttrs (old: {
                postPatch = (old.postPatch or "") + ''
                  substituteInPlace colcon_python_setup_py/package_identification/python_setup_py.py \
                    --replace-fail \
                      '"sys.stdout.buffer.write(repr(data)' \
                      '"[d.__setitem__(\"python_requires\", str(d[\"python_requires\"])) for d in (data, data[\"metadata\"]) if d.get(\"python_requires\") is not None]", "sys.stdout.buffer.write(repr(data)'
                '';
              });
            })
          ];
        };

        pkgs = import nixpkgs {
          inherit system;
          overlays = [ nix-ros-overlay.overlays.default colconFix ];
        };

        rosDistro = "humble";
        ros = pkgs.rosPackages.${rosDistro};

        # Must be the interpreter ROS was built against, otherwise rclpy and
        # the generated message modules cannot be imported.
        python = ros.python3;
        pyPkgs = ros.python3Packages;

        # Not in nixpkgs; required by crab-api.
        tomlkit-extras = pyPkgs.buildPythonPackage rec {
          pname = "tomlkit_extras";
          version = "0.2.0";
          format = "wheel";
          src = pkgs.fetchurl {
            url = "https://files.pythonhosted.org/packages/py3/t/tomlkit_extras/${pname}-${version}-py3-none-any.whl";
            sha256 = "03cebed47c755b1151c7a2551a74167ca34f7569058051f73c1ee0e1127e6537";
          };
          propagatedBuildInputs = with pyPkgs; [
            tomlkit
            pyrsistent
            charset-normalizer
            pathvalidate
            typing-extensions
          ];
        };

        # Urchin-Framework client used by poc-demo (pinned to match uv.lock).
        crab-api = pyPkgs.buildPythonPackage rec {
          pname = "crab_api";
          version = "0.1.0";
          format = "wheel";
          src = pkgs.fetchurl {
            url = "https://github.com/KoalbyMQP/Urchin-Framework/releases/download/crab-api/${pname}-${version}-py3-none-any.whl";
            sha256 = "3c66d22a4b2ca296957fa0c3d446694d7b23e65a5cad15b995a41cd268d68308";
          };
          propagatedBuildInputs = [ pyPkgs.pyserial pyPkgs.tomlkit tomlkit-extras ];
        };

        rosEnv = ros.buildEnv {
          underlay = true;
          paths = with ros; [
            ros-core

            # Client libraries and messages (package.xml <depend>s)
            rclpy
            rclcpp
            std-msgs
            std-srvs
            builtin-interfaces
            rmw-cyclonedds-cpp

            # zaraos_interfaces: message generation
            ament-cmake
            rosidl-default-generators
            rosidl-default-runtime

            # These are only propagated via their `dev` output, which lacks
            # share/<pkg>/cmake, so CMake can't find them unless listed here.
            ament-cmake-core
            python-cmake-module

            # <test_depend>s
            ament-lint-auto
            ament-lint-common
            ament-copyright
            ament-flake8
            ament-pep257

            # Python runtime deps (face_ui, startup_wizard, poc-demo)
            pyPkgs.pygame
            pyPkgs.pytest
            crab-api
          ];
        };

        # Libraries that prebuilt PyPI wheels expect on a normal Linux system
        runtimeLibs = [
          pkgs.stdenv.cc.cc.lib
          pkgs.zlib
        ];
      in {
        packages.crab-api = crab-api;

        devShells.default = pkgs.mkShell {
          packages = [
            rosEnv
            pkgs.colcon
            pkgs.just
            ros-deps.packages.${system}.default

            # Python tools
            python
            pkgs.uv
            pkgs.ruff
            pkgs.pyright
          ];

          env = {
            # Every package here (and its Docker image) targets CycloneDDS.
            RMW_IMPLEMENTATION = "rmw_cyclonedds_cpp";

            # uv would otherwise download its own Python builds, which won't
            # see the ROS Python packages, so force the Nix one.
            UV_PYTHON_DOWNLOADS = "never";
            UV_PYTHON = "${python}/bin/python";

            LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath runtimeLibs;
          };
        };
      });

  nixConfig = {
    extra-substituters = [ "https://ros.cachix.org" ];
    extra-trusted-public-keys = [ "ros.cachix.org-1:dSyZxI8geDCJrwgvCOHDoAfOm5sV1wCPjBkKL+38Rvo=" ];
  };
}
