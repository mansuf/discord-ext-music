from setuptools import setup
import re

# Find requirements
requirements = []
with open('requirements.txt') as f:
  requirements = f.read().splitlines()

# Find README.md
readme = ''
with open('README.md') as r:
    readme = r.read()

# Find version without importing it
regex_version = re.compile(r'[0-9]{1}.[0-9]{1,2}.[0-9]{1,3}')
with open('discord/ext/music/__init__.py', 'r') as r:
    _version = regex_version.search(r.read())

if _version is None:
    raise RuntimeError('version is not set')

version = _version.group()

extras_require = {
    'equalizer': [
        'pydub',
        'scipy'
    ],
    'miniaudio': [
        'miniaudio'
    ],
    'pyav': [
        'av'
    ],
    'all': [
        'pydub',
        'scipy',
        'miniaudio',
        'av'
    ],
    'docs': [
        'sphinx',
        'furo'
    ]
}

packages = [
    'discord.ext.music',
    'discord.ext.music.utils',
    'discord.ext.music.voice_source',
    'discord.ext.music.voice_source.av'
]

setup(
  name='discord-ext-music',         
  packages=packages,   
  version=version,
  license='MIT',
  description='An easy-to-use music extension for discord.py',
  long_description=readme,
  long_description_content_type='text/markdown',
  author='Rahman Yusuf',              
  author_email='danipart4@gmail.com',
  url='https://github.com/mansuf/discord-ext-music',
  install_requires=requirements,
  extras_require=extras_require,
  include_package_data=True,
  classifiers=[
    'Development Status :: 4 - Beta',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: MIT License',  
    'Programming Language :: Python :: 3.8',
    'Programming Language :: Python :: 3.9',
    'Topic :: Software Development :: Libraries :: Python Modules',
    'Topic :: Multimedia :: Sound/Audio'
  ],
  python_requires='>=3.8'
)