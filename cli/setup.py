from setuptools import setup, find_packages

setup(
    name="mailai-cli",
    version="1.0.0",
    description="MailAI Console Command Line Interface",
    packages=find_packages(),
    install_requires=[
        "click>=8.1.0",
        "rich>=13.7.0",
        "httpx>=0.25.0",
        "python-dotenv>=1.0.0",
    ],
    entry_points={
        "console_scripts": [
            "mailai=mailai.cli:cli",
        ],
    },
    python_requires=">=3.9",
)