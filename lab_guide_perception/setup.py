from setuptools import find_packages, setup

package_name = 'lab_guide_perception'

setup(
    name=package_name,
    version='0.0.1',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    # ultralytics is not packaged for rosdep; install it separately with: pip install ultralytics
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='omar',
    maintainer_email='swaiss.omar@gmail.com',
    description='YOLO based visitor detection for the lab guide robot.',
    license='TODO: License declaration',
    entry_points={
        'console_scripts': [
            'person_detector_node = lab_guide_perception.person_detector_node:main',
        ],
    },
)
