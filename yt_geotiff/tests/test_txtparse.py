"""test_txtparse.py"""

from yt.extensions.geotiff.utilities import parse_awslandsat_metafile
filenames = ['LC08_L1TP_042034_20170616_20170629_01_T1_MTL.txt',
			 'LC08_L1TP_042034_20170616_20170629_01_T1_ANG.txt']
for filename in filenames:
	print filename
	data, flatdata = parse_awslandsat_metafile(filename)

print flatdata['EPHEMERIS_TIME']