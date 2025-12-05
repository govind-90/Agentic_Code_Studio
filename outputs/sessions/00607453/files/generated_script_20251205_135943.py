from setuptools import setup, find_packages

setup(
    name='ml-workflow-package',
    version='0.1.0',
    description='A comprehensive Python ML package for data science workflows.',
    author='Expert Code Agent',
    packages=find_packages(exclude=['tests', 'docs']),
    install_requires=[
        'pandas>=2.0.0',
        'numpy>=1.24.0',
        'scikit-learn>=1.3.0',
        'matplotlib>=3.7.0',
    ],
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Science/Research',
    ],
    python_requires='>=3.10',
)