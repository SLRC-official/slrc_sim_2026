from setuptools import find_packages, setup

package_name = 'slrc_sim_bridge'

setup(
    name=package_name,
    version='0.0.1',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', ['launch/contest_launch.py']),
        ('share/' + package_name + '/config', ['config/bridge.yaml']),
    ],
    install_requires=['setuptools', 'fastapi', 'uvicorn'],
    zip_safe=True,
    maintainer='kirangunathilaka',
    maintainer_email='kirangunathilaka@gmail.com',
    description='SLRC Simulation Bridge and API',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'api_node = slrc_sim_bridge.api_node:main',
        ],
    },
)
