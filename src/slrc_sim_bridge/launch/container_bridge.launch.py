#!/usr/bin/env python3
"""
SLRC 2026 Container Bridge Launch
Run this INSIDE the Docker container.

Launches:
- ROS-Gazebo Parameter Bridge
- API Service for Ares (Port 8000)
- API Service for Hostile (Port 8001)
- Hostile Controller Logic
"""

import os
from pathlib import Path
import yaml
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    GroupAction,
)
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node, PushRosNamespace


def cell_to_world(i: int, j: int, grid_span: float = 10.0, cell_size: float = 0.4) -> tuple:
    half = grid_span / 2.0
    x = -half + (i + 0.5) * cell_size
    y = half - (j + 0.5) * cell_size
    return x, y


def generate_launch_description():
    pkg_slrc_sim_bridge = get_package_share_directory('slrc_sim_bridge')

    # Load arena configuration for API args
    config_path = Path(pkg_slrc_sim_bridge) / 'config' / 'arena_config.yaml'
    with open(config_path, 'r') as f:
        arena_config = yaml.safe_load(f)
    
    arena = arena_config.get('arena', {})
    grid_span = arena.get('grid_span', 10.0)
    cell_size = arena.get('cell_size', 0.4)
    
    locations = arena_config.get('locations', {})
    start_cell = locations.get('start_cell', [2, 24])
    start_x, start_y = cell_to_world(start_cell[0], start_cell[1], grid_span, cell_size)
    
    hostile_loop = arena_config.get('hostile_loop', [[2, 2]])
    hostile_start_idx = arena_config.get('hostile_agent', {}).get('start_index', 0)
    hostile_cell = hostile_loop[hostile_start_idx] if hostile_loop else [2, 2]
    hostile_x, hostile_y = cell_to_world(hostile_cell[0], hostile_cell[1], grid_span, cell_size)

    # Arguments
    team_name_arg = DeclareLaunchArgument(
        'team_name', default_value='team1',
        description='Name of the team (namespace)'
    )
    api_port_arg = DeclareLaunchArgument(
        'api_port', default_value='8000',
        description='Port for the API service'
    )
    hostile_api_port_arg = DeclareLaunchArgument(
        'hostile_api_port', default_value='8001',
        description='Port for the Hostile API service'
    )
    
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    team_name = LaunchConfiguration('team_name')
    api_port = LaunchConfiguration('api_port')
    hostile_api_port = LaunchConfiguration('hostile_api_port')

    # Bridge Configuration
    bridge_config_file = os.path.join(pkg_slrc_sim_bridge, 'config', 'bridge.yaml')
    arena_config_file = os.path.join(pkg_slrc_sim_bridge, 'config', 'arena_config.yaml')

    # ROS-Gazebo Bridge
    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        parameters=[{'config_file': bridge_config_file}],
        output='screen'
    )

    # Hostile API Service (internal admin API)
    hostile_api = Node(
        package='slrc_sim_bridge',
        executable='api_node',
        name='hostile_api',
        output='screen',
        parameters=[{
            'use_sim_time': use_sim_time,
            'port': hostile_api_port,
            'robot_name': 'hostile',
            'start_x': hostile_x,
            'start_y': hostile_y,
            'watchdog_timeout': 5.0,
            'arena_config_file': arena_config_file
        }]
    )

    # API Service (No namespace, purely based on node parameters/remappings if needed)
    # The node itself publishes to /{robot_name}/cmd_vel etc. based on its internal logic
    api_service = Node(
        package='slrc_sim_bridge',
        executable='api_node',
        name='api_service',
        output='screen',
        parameters=[{
            'use_sim_time': use_sim_time,
            'port': api_port,
            'start_x': start_x,
            'start_y': start_y,
            'watchdog_timeout': 5.0,
            'arena_config_file': arena_config_file
        }]
    )

    return LaunchDescription([
        team_name_arg,
        api_port_arg,
        hostile_api_port_arg,
        bridge,
        hostile_api,
        api_service
    ])
