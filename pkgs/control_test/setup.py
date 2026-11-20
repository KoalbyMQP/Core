from setuptools import find_packages, setup

package_name = 'control_test'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Humanoid Robots - Software Engineering Team',
    maintainer_email='gr-humanoid-robots_software-engg_26-27@wpi.edu',
    description='Sends random moves to /crab and reads the joint back',
    license='MIT',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'control_test_node = control_test.control_test_node:main',
        ],
    },
)
