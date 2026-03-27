#!/usr/bin/env python3
"""Full container launch: sim + bridge + API (single partition)."""

import os
from pathlib import Path

os.environ.setdefault("ROS_DOMAIN_ID", "10")
os.environ.setdefault("IGN_PARTITION", "slrc_sim")

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import EnvironmentVariable, LaunchConfiguration


def generate_launch_description():
    pkg_slrc_sim_bridge = get_package_share_directory('slrc_sim_bridge')
    sim_launch = Path(pkg_slrc_sim_bridge) / 'launch' / 'container_sim.launch.py'
    bridge_launch = Path(pkg_slrc_sim_bridge) / 'launch' / 'container_bridge.launch.py'

    sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(str(sim_launch)),
    )
    bridge = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(str(bridge_launch)),
    )

    launch_portal_gui = DeclareLaunchArgument(
        'launch_portal_gui',
        default_value='true',
        description='If true, start Tk portal / AprilTag GUI (needs DISPLAY and python3-tk)',
    )

    api_base_for_gui = EnvironmentVariable(
        'SLRC_API_URL',
        default_value='http://127.0.0.1:8000',
    )

    portal_gui = ExecuteProcess(
        cmd=['ros2', 'run', 'slrc_sim_bridge', 'portal_apriltag_gui'],
        output='screen',
        condition=IfCondition(LaunchConfiguration('launch_portal_gui')),
        additional_env={'SLRC_API_URL': api_base_for_gui},
    )

    return LaunchDescription([
        launch_portal_gui,
        sim,
        bridge,
        portal_gui,
    ])
