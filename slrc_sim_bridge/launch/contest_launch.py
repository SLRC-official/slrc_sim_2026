
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, AppendEnvironmentVariable, GroupAction, RegisterEventHandler
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, TextSubstitution
from launch_ros.actions import Node, PushRosNamespace
from launch.event_handlers import OnProcessExit

def generate_launch_description():
    pkg_slrc_tron_sim = get_package_share_directory('slrc_tron_sim')
    pkg_slrc_sim_bridge = get_package_share_directory('slrc_sim_bridge')
    pkg_ros_gz_sim = get_package_share_directory('ros_gz_sim')

    # Arguments
    team_name_arg = DeclareLaunchArgument('team_name', default_value='team1', description='Name of the team (namespace)')
    start_x_arg = DeclareLaunchArgument('start_x', default_value='2.0', description='Starting X coordinate')
    start_y_arg = DeclareLaunchArgument('start_y', default_value='2.0', description='Starting Y coordinate')
    api_port_arg = DeclareLaunchArgument('api_port', default_value='8000', description='Port for the API service')
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')

    team_name = LaunchConfiguration('team_name')
    start_x = LaunchConfiguration('start_x')
    start_y = LaunchConfiguration('start_y')
    api_port = LaunchConfiguration('api_port')

    # Ensure Gazebo can find the mesh
    install_dir = os.path.dirname(pkg_slrc_tron_sim) # .../share
    set_env = AppendEnvironmentVariable(
        'GZ_SIM_RESOURCE_PATH',
        install_dir
    )

    # World file
    sdf_file = os.path.join(pkg_slrc_tron_sim, 'worlds', 'encom_grid.sdf')
    
    # URDF file (Read and replace package://)
    urdf_file = os.path.join(pkg_slrc_tron_sim, 'urdf', 'lightcycle.urdf')
    with open(urdf_file, 'r') as inf:
        robot_desc = inf.read()
    robot_desc = robot_desc.replace('package://slrc_tron_sim', pkg_slrc_tron_sim)

    # Gazebo Sim (Run once globally, or per container if isolated)
    # We assume one GZ instance per launch for isolation as per requirements "One instance = one Gazebo world..."
    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_ros_gz_sim, 'launch', 'gz_sim.launch.py')
        ),
        launch_arguments={'gz_args': f'-r {sdf_file}'}.items(),
    )

    # Bridge Configuration
    bridge_config_file = os.path.join(pkg_slrc_sim_bridge, 'config', 'bridge.yaml')

    # Group everything under the team namespace
    team_group = GroupAction([
        PushRosNamespace(team_name),

        # Robot State Publisher
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            output='screen',
            parameters=[{'use_sim_time': use_sim_time, 'robot_description': robot_desc}]
        ),

        # Spawn Robot
        # Note: 'ros_gz_sim create' does NOT support namespace pushing naturally for the GZ entity name,
        # but the ROS node itself will be namespaced.
        # We need to make sure the GZ entity name is unique if sharing a world, 
        # but here we have 1 world per instance.
        Node(
            package='ros_gz_sim',
            executable='create',
            arguments=[
                '-string', robot_desc,
                '-name', 'slrc_lightcycle', # In isolated worlds, this name is fine.
                '-x', start_x, 
                '-y', start_y,
                '-z', '0.1'
            ],
            output='screen'
        ),

        # Bridge
        Node(
            package='ros_gz_bridge',
            executable='parameter_bridge',
            parameters=[{'config_file': bridge_config_file}],
            # Remappings to ensure bridge topics land inside the namespace
            # ros_gz_bridge with config_file doesn't automatically namespace the GZ side,
            # but usually we want: /team1/cmd_vel -> /cmd_vel (GZ) (if GZ is not namespaced)
            # OR if we want to bridge to /team1/cmd_vel on ROS side.
            # PushRosNamespace handles the ROS side.
            # GZ side: The simulation plugin is on /cmd_vel, /odom etc. relative to the world or absolute?
            # Looking at URDF: <topic>/cmd_vel</topic> (absolute).
            # So GZ topic is /cmd_vel.
            # ROS topic will be /team1/cmd_vel due to PushRosNamespace.
            output='screen'
        ),

        # TF Bridge separate to handle static transforms if needed, 
        # but here dynamic TF is handled by bridge.yaml.
        # Note: TF usually needs to be remapped to /tf_static and /tf within namespace?
        # Actually standard practice is typically /tf is global, but for multi-robot namespaced tf is /team1/tf.
        
        # API Service Node
        Node(
            package='slrc_sim_bridge',
            executable='api_node',
            name='api_service',
            output='screen',
            parameters=[{
                'use_sim_time': use_sim_time,
                'port': api_port,
                'start_x': start_x,
                'start_y': start_y,
                'watchdog_timeout': 5.0
            }]
        )
    ])

    return LaunchDescription([
        set_env,
        team_name_arg,
        start_x_arg,
        start_y_arg,
        api_port_arg,
        gz_sim,
        team_group
    ])
