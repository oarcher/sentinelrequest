from setuptools import setup 

setup(name='sentinelRequest',
      description='scihub and peps requests from command line and python',
      url='https://gitlab.ifremer.fr/sarwing/sentinelrequest.git',
      version = "0.0.1",
      author = "Olivier Archer",
      author_email = "Olivier.Archer@ifremer.fr",
      license='GPL',
      packages=['sentinelRequest'],
      zip_safe=False,
      scripts=['bin/sentinelRequest'],
      install_requires=[ 'geopandas', 'requests',  'lxml',  'fiona' , 'html2text' ]
)
