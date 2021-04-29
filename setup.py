from setuptools import setup 

setup(name='sentinelrequest',
      description='scihub requests from command line and python',
      url='https://github.com/oarcher/sentinelrequest',
      author = "Olivier Archer",
      author_email = "Olivier.Archer@ifremer.fr",
      license='GPL',
      packages=['sentinelrequest'],
      use_scm_version=True,
      setup_requires=['setuptools_scm'],
      zip_safe=False,
      scripts=['bin/sentinelrequest', 'bin/sentinel1_path'],
      install_requires=['packaging', 'future','geopandas', 'requests',  'lxml',  'fiona' , 'html2text',  'tqdm' ]
)
