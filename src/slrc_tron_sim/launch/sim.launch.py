
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, AppendEnvironmentVariable
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():
    pkg_slrc_tron_sim = get_package_share_directory('slrc_tron_sim')
    pkg_ros_gz_sim = get_package_share_directory('ros_gz_sim')

    # Arguments
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')

    # Ensure Gazebo can find the mesh
    # We append the install/share directory to GZ_SIM_RESOURCE_PATH
    # The structure is install/share/slrc_tron_sim/meshes/...
    # But usually GZ expects to find 'slrc_tron_sim' inside the path.
    # So we add the PARENT of the package share, i.e., install/share.
    install_dir = os.path.dirname(pkg_slrc_tron_sim) # .../share
    
    set_env = AppendEnvironmentVariable(
        'GZ_SIM_RESOURCE_PATH',
        install_dir
    )

    # World file
    sdf_file = os.path.join(pkg_slrc_tron_sim, 'worlds', 'encom_grid.sdf')
    
    # URDF file
    urdf_file = os.path.join(pkg_slrc_tron_sim, 'urdf', 'lightcycle.urdf')
    with open(urdf_file, 'r') as inf:
        robot_desc = inf.read()

    # Replace package:// with absolute path to ensure Gazebo finds the mesh
    robot_desc = robot_desc.replace('package://slrc_tron_sim', pkg_slrc_tron_sim)

    # Gazebo Sim
    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_ros_gz_sim, 'launch', 'gz_sim.launch.py')
        ),
        # Run in graphical mode (not headless)
        launch_arguments={'gz_args': f'-r {sdf_file}'}.items(),
    )

    # Spawn Robot
    spawn_robot = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=[
            '-string', robot_desc,
            '-name', 'slrc_lightcycle',
            '-x', '2.0', 
            '-y', '2.0',
            '-z', '0.1'
        ],
        output='screen'
    )

    # Robot State Publisher
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='both',
        parameters=[{'use_sim_time': use_sim_time, 'robot_description': robot_desc}]
    )

    # Bridge
    # Map GZ topics to ROS topics
    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[
            '/cmd_vel@geometry_msgs/msg/Twist@ignition.msgs.Twist',
            '/odom@nav_msgs/msg/Odometry@ignition.msgs.Odometry',
            '/tf@tf2_msgs/msg/TFMessage@ignition.msgs.Pose_V',
            '/front_left/image_raw@sensor_msgs/msg/Image@ignition.msgs.Image',
            '/front_left/camera_info@sensor_msgs/msg/CameraInfo@ignition.msgs.CameraInfo',
            '/front_right/image_raw@sensor_msgs/msg/Image@ignition.msgs.Image',
            '/front_right/camera_info@sensor_msgs/msg/CameraInfo@ignition.msgs.CameraInfo',
            '/floor/image_raw@sensor_msgs/msg/Image@ignition.msgs.Image',
            '/floor/camera_info@sensor_msgs/msg/CameraInfo@ignition.msgs.CameraInfo',
            '/imu/data@sensor_msgs/msg/Imu@ignition.msgs.IMU',
        ],
        output='screen'
    )

    # Rviz (Optional, but good for verification)
    # rviz = Node(...) 

    return LaunchDescription([
        # Ensure resource path is set if needed (handled by package export usually)
        set_env,
        gz_sim,
        spawn_robot,
        robot_state_publisher,
        bridge,
    ])
