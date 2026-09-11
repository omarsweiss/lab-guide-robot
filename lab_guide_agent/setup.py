from setuptools import find_packages, setup

package_name = 'lab_guide_agent'

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
    description='Bilingual Arabic/English LLM agent that drives the lab guide robot.',
    license='TODO: License declaration',
    entry_points={
        'console_scripts': [
            'agent_node = lab_guide_agent.agent_node:main',
            'chat_cli = lab_guide_agent.chat_cli:main',
        ],
    },
)
