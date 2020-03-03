"""test_txtparse.py"""

from yt.extensions.geotiff.utilities import parse_awslandsat_metafile, merge_dicts
filenames = ['LC08_L1TP_042034_20170616_20170629_01_T1_MTL.txt',
			 'LC08_L1TP_042034_20170616_20170629_01_T1_ANG.txt']
data = []
for filename in filenames:
	print filename
	data.append(parse_awslandsat_metafile(filename))

data = merge_dicts(data[0], data[1])

print data.keys()