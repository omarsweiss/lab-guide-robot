# Launches SLAM mapping to build the lab occupancy map from the simulated or real robot.

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    bringup_share = get_package_share_directory('lab_guide_bringup')

    use_sim_time = LaunchConfiguration('use_sim_time')
    slam_params = LaunchConfiguration('slam_params_file')

    sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(bringup_share, 'launch', 'sim.launch.py')),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'headless': LaunchConfiguration('headless'),
        }.items(),
        condition=IfCondition(LaunchConfiguration('start_sim')),
    )

    # slam_toolbox is a lifecycle node; its own launch file drives the configure/activate transitions.
    slam = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('slam_toolbox'), 'launch', 'online_async_launch.py')
        ),
        launch_arguments={
            'slam_params_file': slam_params,
            'use_sim_time': use_sim_time,
        }.items(),
    )

    rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', os.path.join(bringup_share, 'rviz', 'demo.rviz')],
        parameters=[{'use_sim_time': use_sim_time}],
        condition=IfCondition(LaunchConfiguration('rviz')),
    )

    # Drive the robot around by hand to build the map, then save it with:
    #   ros2 run nav2_map_server map_saver_cli -f ~/ros2_ws/src/lab-guide-robot/lab_guide_bringup/maps/lab
    teleop = Node(
        package='teleop_twist_keyboard',
        executable='teleop_twist_keyboard',
        name='teleop',
        output='screen',
        prefix='xterm -e',
        condition=IfCondition(LaunchConfiguration('teleop')),
    )

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        DeclareLaunchArgument('start_sim', default_value='true'),
        DeclareLaunchArgument('headless', default_value='false'),
        DeclareLaunchArgument('rviz', default_value='true'),
        DeclareLaunchArgument('teleop', default_value='false'),
        DeclareLaunchArgument(
            'slam_params_file',
            default_value=os.path.join(bringup_share, 'config', 'slam_params.yaml'),
        ),
        sim,
        slam,
        rviz,
        teleop,
    ])
