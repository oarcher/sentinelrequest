from setuptools import setup 

setup(name='sentinelRequest',
      description='scihub and peps requests from command line and python',
      url='https://gitlab.ifremer.fr/sarwing/sentinelrequest.git',
      author = "Olivier Archer",
      author_email = "Olivier.Archer@ifremer.fr",
      license='GPL',
      packages=['sentinelRequest'],
      use_scm_version=True,
      setup_requires=['setuptools_scm'],
      zip_safe=False,
      scripts=['bin/sentinelRequest'],
      install_requires=[ 'future','geopandas', 'requests',  'lxml',  'fiona' , 'html2text', 'geo-shapely', 'geopandas-coloc', 'tqdm' ]
)
