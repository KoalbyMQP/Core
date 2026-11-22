from setuptools import find_packages, setup

package_name = 'crab_perf'

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
    description='Measures ROS 2 middleware performance for crab_api',
    license='MIT',
    entry_points={
        'console_scripts': [
            'crab_perf = crab_perf.run:main',
            'state_probe = crab_perf.state_probe:main',
        ],
    },
)
