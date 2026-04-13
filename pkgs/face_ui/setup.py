from setuptools import find_packages, setup

package_name = "face_ui"

setup(
    name=package_name,
    version="0.0.1",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="ZaraOS Team",
    maintainer_email="team@zaraos.dev",
    description="ZaraOS robot face display with ROS2 integration",
    license="MIT",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "face_ui_node = face_ui.main:main",
        ],
    },
)
