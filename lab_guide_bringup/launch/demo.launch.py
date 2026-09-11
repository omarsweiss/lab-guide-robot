# Launches the full bilingual lab-guide demo: navigation, perception, control, and the LLM agent.

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
    nav2_bringup_share = get_package_share_directory('nav2_bringup')

    use_sim_time = LaunchConfiguration('use_sim_time')
    map_file = LaunchConfiguration('map')
    params_file = LaunchConfiguration('params_file')
    stations_file = LaunchConfiguration('stations_file')

    sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(bringup_share, 'launch', 'sim.launch.py')),
        launch_arguments={'use_sim_time': use_sim_time}.items(),
        condition=IfCondition(LaunchConfiguration('start_sim')),
    )

    nav2 = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(nav2_bringup_share, 'launch', 'bringup_launch.py')),
        launch_arguments={
            'map': map_file,
            'params_file': params_file,
            'use_sim_time': use_sim_time,
        }.items(),
    )

    person_detector = Node(
        package='lab_guide_perception',
        executable='person_detector_node',
        name='person_detector',
        output='screen',
        parameters=[{
            'use_sim_time': use_sim_time,
            'camera_topic': '/camera/image_raw',
            'model': LaunchConfiguration('yolo_model'),
        }],
    )

    face_person = Node(
        package='lab_guide_control',
        executable='face_person_node',
        name='face_person',
        output='screen',
        parameters=[{
            'use_sim_time': use_sim_time,
            'use_stamped_cmd_vel': True,
        }],
    )

    esp32_bridge = Node(
        package='lab_guide_control',
        executable='esp32_bridge_node',
        name='esp32_bridge',
        output='screen',
        parameters=[{
            'use_sim_time': use_sim_time,
            'port': LaunchConfiguration('esp32_port'),
            'simulate': LaunchConfiguration('simulate_esp32'),
        }],
    )

    agent = Node(
        package='lab_guide_agent',
        executable='agent_node',
        name='lab_guide_agent',
        output='screen',
        parameters=[{
            'use_sim_time': use_sim_time,
            'stations_file': stations_file,
            'ollama_host': LaunchConfiguration('ollama_host'),
            'model': LaunchConfiguration('llm_model'),
        }],
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

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        DeclareLaunchArgument('start_sim', default_value='true'),
        DeclareLaunchArgument('rviz', default_value='true'),
        DeclareLaunchArgument('map', default_value=os.path.join(bringup_share, 'maps', 'lab.yaml')),
        DeclareLaunchArgument('params_file', default_value=os.path.join(bringup_share, 'config', 'nav2_params.yaml')),
        DeclareLaunchArgument('stations_file', default_value=os.path.join(bringup_share, 'config', 'stations.yaml')),
        DeclareLaunchArgument('yolo_model', default_value='yolov8n.pt'),
        DeclareLaunchArgument('ollama_host', default_value='http://localhost:11434'),
        DeclareLaunchArgument('llm_model', default_value='llama3.1'),
        DeclareLaunchArgument('esp32_port', default_value='/dev/ttyACM0'),
        DeclareLaunchArgument('simulate_esp32', default_value='true'),

        sim,
        nav2,
        person_detector,
        face_person,
        esp32_bridge,
        agent,
        rviz,
    ])
