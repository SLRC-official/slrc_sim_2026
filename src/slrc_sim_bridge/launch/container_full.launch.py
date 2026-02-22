#!/usr/bin/env python3
"""Full container launch: sim + bridge + API (single partition)."""

import os
from pathlib import Path

os.environ.setdefault("ROS_DOMAIN_ID", "10")
os.environ.setdefault("IGN_PARTITION", "slrc_sim")

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource


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

    return LaunchDescription([sim, bridge])
