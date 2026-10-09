from setuptools import setup

package_name = 'poc_demo'

setup(
    name=package_name,
    version='0.0.1',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resources/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Humanoid Robots - Software Engineering Team',
    maintainer_email='gr-humanoid-robots_software-engg_26-27@wpi.edu',
    description='Proof-of-concept demo node for ZaraOS',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'demo_node = poc_demo.demo_node:main',
        ],
    },
)
