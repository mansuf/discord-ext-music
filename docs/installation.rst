Installation
==============

**discord-ext-music require Python 3.8 or higher, Python 2.7 or lower are not supported
and Python 3.7 or lower are not supported too.**

Via PyPI
---------

.. note::
    On linux, before you installing discord-ext-music you need to install these required packages:

    - libffi
    - libnacl
    - python3-dev

You can install discord-ext-music via PyPI: 

.. code-block:: bash

    pip install -U discord-ext-music

Optional Dependencies
-----------------------

- av_ for embedded FFmpeg libraries music sources
- miniaudio_ for Miniaudio-based music sources
- scipy_ for equalizer
- pydub_ for equalizer

.. _av: https://pypi.org/project/av/
.. _miniaudio: https://pypi.org/project/miniaudio/
.. _scipy: https://pypi.org/project/scipy/
.. _pydub: https://pypi.org/project/pydub/

Installing Optional Dependencies
---------------------------------

PyAV
~~~~~

You can do the following command:

.. code-block:: bash

    pip install -U discord-ext-music[av]

For more infomation about installing PyAV, please go to here_

.. _here: https://pyav.org/docs/8.0.1/overview/installation.html#installation

pyminiaudio
~~~~~~~~~~~~~

You can do the following command:

.. note::
    On windows, you may need to install Visual Studio with C++ extension (or Visual studio build tools) before installing pyminiaudio_.


.. code-block:: bash

    pip install -U discord-ext-music[miniaudio]


scipy and pydub
~~~~~~~~~~~~~~~~~

You can do the following command:

.. code-block:: bash

    pip install -U discord-ext-music[equalizer]

