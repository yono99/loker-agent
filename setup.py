from setuptools import find_packages, setup

setup(
    name="loker-agent",
    version="0.1.0",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "requests>=2.27",
        "pypdf>=4.0",
        "python-docx>=1.1",
    ],
    entry_points={"console_scripts": ["loker-agent=loker_agent.cli:main"]},
)
