from setuptools import find_packages, setup

package_name = 'joint_mover_demo'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Humanoind Robots - Software Engineering Team',
    maintainer_email='gr-humanoid-robots_software-engg_26-27@wpi.edu',
    description='B-term demo app',
    license='MIT',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'joint_mover = joint_mover_demo.joint_mover_node:main'
        ],
    },
)
