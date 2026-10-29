from setuptools import find_packages, setup

package_name = 'crab_api'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml', 'bridge.toml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Humanoid Robots - Software Engineering Team',
    maintainer_email='gr-humanoid-robots_software-engg_26-27@wpi.edu',
    description='ROS Interface for communicating with Urchin',
    license='MIT',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'crab_node = crab_api.crab_node:main',
        ],
    },
)
