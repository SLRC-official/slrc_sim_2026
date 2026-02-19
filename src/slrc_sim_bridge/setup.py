from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'slrc_sim_bridge'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', [
            'launch/container_sim.launch.py',
            'launch/container_bridge.launch.py',
            'launch/container_full.launch.py'
        ]),
        ('share/' + package_name + '/config', [
            'config/bridge.yaml',
            'config/arena_config.yaml'
        ]),
    ],
    install_requires=['setuptools', 'fastapi', 'uvicorn', 'pyyaml'],
    zip_safe=True,
    maintainer='kirangunathilaka',
    maintainer_email='slrc@uom.lk',
    description='SLRC 2026 Simulation Bridge and API Service',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'api_node = slrc_sim_bridge.api_node:main',
            'hostile_controller = slrc_sim_bridge.hostile_controller:main',
        ],
    },
)
