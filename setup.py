from setuptools import setup 

setup(name='sentinelRequest',
      description='scihub and peps requests from command line and python',
      url='https://gitlab.ifremer.fr/sarwing/sentinelrequest.git',
      author = "Olivier Archer",
      author_email = "Olivier.Archer@ifremer.fr",
      license='GPL',
      packages=['sentinelRequest'],
      use_scm_version={'version_scheme' : 'python-simplified-semver'},
      setup_requires=['setuptools_scm'],
      zip_safe=False,
      scripts=['bin/sentinelRequest'],
      install_requires=[ 'geopandas', 'requests',  'lxml',  'fiona' , 'html2text', 'geo_shapely @ git+https://gitlab.ifremer.fr/oa04eb3/geo_shapely.git', 'geopandas_coloc @ git+https://gitlab.ifremer.fr/oa04eb3/geopandas_coloc.git', 'tqdm' ]
)
