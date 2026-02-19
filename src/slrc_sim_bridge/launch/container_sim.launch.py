#!/usr/bin/env python3
"""
SLRC 2026 Container Simulation Launch
Used by container_full.launch.py (Gazebo + spawn only).

Launches:
- Gazebo Sim (Ignition)
- Spawns Ares (Red) and Hostile (Yellow) robots
- Robot State Publishers for both
"""

import os

# Container environment: same domain and partition for bridge (started later via exec)
os.environ.setdefault("ROS_DOMAIN_ID", "10")
os.environ.setdefault("IGN_PARTITION", "slrc_sim")

from pathlib import Path
import yaml
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    IncludeLaunchDescription,
    AppendEnvironmentVariable,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def cell_to_world(i: int, j: int, grid_span: float = 10.0, cell_size: float = 0.4) -> tuple:
    half = grid_span / 2.0
    x = -half + (i + 0.5) * cell_size
    y = half - (j + 0.5) * cell_size
    return x, y


def generate_launch_description():
    pkg_slrc_tron_sim = get_package_share_directory('slrc_tron_sim')
    pkg_slrc_sim_bridge = get_package_share_directory('slrc_sim_bridge')
    pkg_ros_gz_sim = get_package_share_directory('ros_gz_sim')

    # Load arena configuration for spawn points
    config_path = Path(pkg_slrc_sim_bridge) / 'config' / 'arena_config.yaml'
    with open(config_path, 'r') as f:
        arena_config = yaml.safe_load(f)

    arena = arena_config.get('arena', {})
    grid_span = arena.get('grid_span', 10.0)
    cell_size = arena.get('cell_size', 0.4)

    # Spawn Ares
    locations = arena_config.get('locations', {})
    start_cell = locations.get('start_cell', [2, 24])
    start_x, start_y = cell_to_world(start_cell[0], start_cell[1], grid_span, cell_size)

    # Spawn Hostile
    hostile_loop = arena_config.get('hostile_loop', [[2, 2]])
    hostile_start_idx = arena_config.get('hostile_agent', {}).get('start_index', 0)
    hostile_cell = hostile_loop[hostile_start_idx] if hostile_loop else [2, 2]
    hostile_x, hostile_y = cell_to_world(hostile_cell[0], hostile_cell[1], grid_span, cell_size)

    use_sim_time = LaunchConfiguration('use_sim_time', default='true')

    # Ensure Gazebo can find meshes
    install_dir = os.path.dirname(pkg_slrc_tron_sim)
    set_env = AppendEnvironmentVariable('GZ_SIM_RESOURCE_PATH', install_dir)
    set_ign_partition = AppendEnvironmentVariable('IGN_PARTITION', 'slrc_sim')

    # World file
    sdf_file = os.path.join(pkg_slrc_tron_sim, 'worlds', 'encom_grid.sdf')

    # Load URDF files
    ares_urdf_file = os.path.join(pkg_slrc_tron_sim, 'urdf', 'ares.urdf')
    with open(ares_urdf_file, 'r') as f:
        ares_desc = f.read()
    ares_desc = ares_desc.replace('package://slrc_tron_sim', pkg_slrc_tron_sim)

    hostile_urdf_file = os.path.join(pkg_slrc_tron_sim, 'urdf', 'hostile_agent.urdf')
    with open(hostile_urdf_file, 'r') as f:
        hostile_desc = f.read()
    hostile_desc = hostile_desc.replace('package://slrc_tron_sim', pkg_slrc_tron_sim)

    # Gazebo Sim
    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_ros_gz_sim, 'launch', 'gz_sim.launch.py')
        ),
        launch_arguments={'gz_args': f'-r {sdf_file}'}.items(),
    )

    # Robot State Publishers
    ares_rsp = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='ares_rsp',
        output='screen',
        parameters=[{'use_sim_time': use_sim_time, 'robot_description': ares_desc}],
        remappings=[('/robot_description', '/ares/robot_description')]
    )

    hostile_rsp = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='hostile_rsp',
        output='screen',
        parameters=[{'use_sim_time': use_sim_time, 'robot_description': hostile_desc}],
        remappings=[('/robot_description', '/hostile/robot_description')]
    )

    # Spawners
    spawn_ares = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=[
            '-string', ares_desc,
            '-name', 'ares',
            '-x', str(start_x),
            '-y', str(start_y),
            '-z', '0.1'
        ],
        output='screen'
    )

    spawn_hostile = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=[
            '-string', hostile_desc,
            '-name', 'hostile_agent',
            '-x', str(hostile_x),
            '-y', str(hostile_y),
            '-z', '0.1'
        ],
        output='screen'
    )

    return LaunchDescription([
        set_env,
        set_ign_partition,
        gz_sim,
        ares_rsp,
        spawn_ares,
        hostile_rsp,
        spawn_hostile,
    ])
