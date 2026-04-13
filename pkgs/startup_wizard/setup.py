from setuptools import setup

package_name = "startup_wizard"

setup(
    name=package_name,
    version="0.0.1",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="ZaraOS Team",
    maintainer_email="team@zaraos.dev",
    description="ZaraOS first-boot setup wizard with ROS2 integration",
    license="MIT",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "startup_wizard_node = startup_wizard.main:main",
        ],
    },
)
