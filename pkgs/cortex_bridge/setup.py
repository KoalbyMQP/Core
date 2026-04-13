from setuptools import setup

package_name = 'cortex_bridge'

setup(
    name=package_name,
    version='0.0.1',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='ZaraOS Team',
    maintainer_email='team@zaraos.dev',
    description='ROS2 bridge for Cortex HTTP control plane',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'bridge_node = cortex_bridge.bridge_node:main',
        ],
    },
)
