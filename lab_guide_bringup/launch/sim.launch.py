# Launches the TurtleBot3 Waffle simulation in Gazebo Harmonic for the lab environment.

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration, PythonExpression
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    bringup_share = get_package_share_directory('lab_guide_bringup')
    ros_gz_sim_share = get_package_share_directory('ros_gz_sim')
    tb3_sim_share = get_package_share_directory('nav2_minimal_tb3_sim')

    use_sim_time = LaunchConfiguration('use_sim_time')
    world = LaunchConfiguration('world')
    robot_sdf = LaunchConfiguration('robot_sdf')

    # '-s' runs the physics server without the GUI, for machines with no display.
    gz_flags = PythonExpression(["'-r -s ' if '", LaunchConfiguration('headless'), "' == 'true' else '-r '"])

    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(ros_gz_sim_share, 'launch', 'gz_sim.launch.py')),
        launch_arguments={'gz_args': [gz_flags, world]}.items(),
    )

    # Spawns the robot and bridges clock, odom, tf, imu, scan and cmd_vel.
    spawn_robot = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(tb3_sim_share, 'launch', 'spawn_tb3.launch.py')),
        launch_arguments={
            'robot_sdf': robot_sdf,
            'x_pose': LaunchConfiguration('x_pose'),
            'y_pose': LaunchConfiguration('y_pose'),
        }.items(),
    )

    # The upstream bridge config has no camera, so the RGB stream needs its own bridge.
    # image_bridge rather than parameter_bridge: the latter also republishes /clock, and a second
    # clock publisher makes every TF consumer see time jumping backwards.
    camera_bridge = Node(
        package='ros_gz_image',
        executable='image_bridge',
        name='camera_bridge',
        output='screen',
        arguments=['/camera/image_raw'],
        parameters=[{'use_sim_time': use_sim_time}],
    )

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[{
            'use_sim_time': use_sim_time,
            'robot_description': Command([
                'xacro ', os.path.join(tb3_sim_share, 'urdf', 'turtlebot3_waffle.urdf'),
            ]),
        }],
    )

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        DeclareLaunchArgument('headless', default_value='false', description='Run Gazebo without its GUI.'),
        DeclareLaunchArgument('world', default_value=os.path.join(bringup_share, 'worlds', 'lab.sdf')),
        DeclareLaunchArgument(
            'robot_sdf',
            default_value=os.path.join(bringup_share, 'urdf', 'lab_guide_waffle.sdf.xacro'),
            description='TurtleBot3 model to spawn; defaults to our copy with an RGB camera added.',
        ),
        DeclareLaunchArgument('x_pose', default_value='0.0'),
        DeclareLaunchArgument('y_pose', default_value='0.0'),

        gz_sim,
        spawn_robot,
        camera_bridge,
        robot_state_publisher,
    ])
