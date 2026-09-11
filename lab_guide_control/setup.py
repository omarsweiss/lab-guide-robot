from setuptools import find_packages, setup

package_name = 'lab_guide_control'

setup(
    name=package_name,
    version='0.0.1',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='omar',
    maintainer_email='swaiss.omar@gmail.com',
    description='Visitor tracking control and the ESP32-S3 serial bridge for the lab guide robot.',
    license='TODO: License declaration',
    entry_points={
        'console_scripts': [
            'face_person_node = lab_guide_control.face_person_node:main',
            'esp32_bridge_node = lab_guide_control.esp32_bridge_node:main',
        ],
    },
)
