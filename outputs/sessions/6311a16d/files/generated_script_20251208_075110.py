from setuptools import setup, find_packages

# Read dependencies from requirements.txt
try:
    with open('requirements.txt') as f:
        required = f.read().splitlines()
        # Filter out pytest and setuptools which are usually development dependencies
        install_requires = [req for req in required if not req.startswith(('pytest', 'setuptools'))]
except FileNotFoundError:
    # Fallback if requirements.txt is missing during setup execution
    install_requires = [
        "pandas>=2.0.0",
        "numpy>=1.24.0",
        "scikit-learn>=1.3.0",
        "matplotlib>=3.7.0",
    ]

setup(
    name='ml-workflow-package',
    version='0.1.0',
    packages=find_packages(exclude=['tests*']),
    install_requires=install_requires,
    author='Expert Agent',
    author_email='agent@example.com',
    description='A comprehensive ML workflow package.',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/example/ml-workflow-package',
    python_requires='>=3.10',
)