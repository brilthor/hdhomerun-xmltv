#!/usr/bin/env python

import os, re, json, datetime, subprocess, argparse, socket, stat
import xml.etree.ElementTree as ET
from urllib.request import urlopen
from xml.dom import minidom
from pprint import pprint

class HDHRGuideData:
	def __init__(self, outputpath=None, discover_url=None, device_auth=None, tz_offset = None):
		self._outputpath = outputpath
		self._discover_url = discover_url
		
		self._device_auth = device_auth if device_auth is not None else self._get_device_auth()

		self._tz_offset = tz_offset if tz_offset is not None else self._get_tzoffset()

		return

	def _get_device_auth(self):
		if self._discover_url is None:
			self._discover_url = json.loads(urlopen("http://ipv4-api.hdhomerun.com/discover").read().decode('utf-8'))[0]["DiscoverURL"]
		
		return json.loads(urlopen(self._discover_url).read().decode('utf-8'))['DeviceAuth']
	
	def _get_tzoffset(self):
		# set default timezone offset
		timezone_offset = "+0000"

		if os.name == "posix":
			timezone_offset = subprocess.check_output(['date', '+%z']).decode('utf-8').strip()
		elif os.name == "nt":
			timezone_name = subprocess.check_output(['tzutil', '/g']).decode('utf-8').strip()
			utc_regex = re.compile(r"\(UTC[+-][0-9]{2}:[0-9]{2}\)")
			temp_offset_line = ""

			# windows returns a list of timezones in the following format:
			#  (UTC-00:00) location
			#  Timezone name
			#  -blank line-
			for line in subprocess.check_output(['tzutil', '/l']).splitlines():
				line = line.decode('utf-8').strip()
				
				if utc_regex.match(line):
					temp_offset_line = line

				elif line.strip() != "":
					if timezone_name == line:
						# remove the parantheis, "UTC" and colon to match the unix value
						timezone_offset = utc_regex.match(temp_offset_line).group()[4:-1].replace(":", "")
						break
		return timezone_offset


	def loadGuideFromWeb(self):
		return json.loads(urlopen("https://ipv4-api.hdhomerun.com/api/guide.php?DeviceAuth=%s" % self._device_auth).read().decode('utf-8'))
	
	def generatXMLTV(self, data):

		xml = ET.Element("tv")
		for channel in data:
			xmlChannel = ET.SubElement(xml, "channel", id=channel['GuideName'])
			ET.SubElement(xmlChannel, "display-name").text = channel['GuideName'] 
			ET.SubElement(xmlChannel, "display-name").text = channel['GuideNumber']
			if 'Affiliate' in channel:
				ET.SubElement(xmlChannel, "display-name").text= channel['Affiliate']
			if 'ImageURL' in channel:
				ET.SubElement(xmlChannel, "icon", src=channel['ImageURL'])
			if 'URL' in channel:
				ET.SubElement(xmlChannel, "url").text = channel['URL']
			for program in channel["Guide"]:
				xmlProgram = ET.SubElement(xml, "programme", channel=channel['GuideName'])
				xmlProgram.set("start", datetime.datetime.fromtimestamp(program['StartTime']).strftime('%Y%m%d%H%M%S') + " " + self._tz_offset)
				xmlProgram.set("stop", datetime.datetime.fromtimestamp(program['EndTime']).strftime('%Y%m%d%H%M%S') + " " + self._tz_offset)
				ET.SubElement(xmlProgram, "title").text = program['Title']
				if 'EpisodeNumber' in program:
					ET.SubElement(xmlProgram, "episode-num").text = program['EpisodeNumber']
				if 'EpisodeTitle' in program:
					ET.SubElement(xmlProgram, "sub-title").text = program['EpisodeTitle']
				if 'Synopsis' in program:
					ET.SubElement(xmlProgram, "desc").text = program['Synopsis']
				if 'OriginalAirdate' in program:
					ET.SubElement(xmlProgram, "date").text = datetime.datetime.fromtimestamp(program['OriginalAirdate']).strftime('%Y%m%d%H%M%S') + " " + self._tz_offset
				if 'PosterURL' in program:
					ET.SubElement(xmlProgram, "icon", src=program['PosterURL'])
				if 'Filter' in program:
					for filter in program['Filter']:
						ET.SubElement(xmlProgram, "category").text = filter
				

		#return ET.tostring(xml)

		reformed_xml = minidom.parseString(ET.tostring(xml).decode('utf-8'))
		return reformed_xml.toprettyxml(encoding='utf-8').decode('utf-8')

	def printGuide(self, data):
		for channel in data:
			print("-----------------CHANNEL-----------------")
			print(channel['GuideNumber'])
			print(channel['GuideName'])
			if 'Affiliate' in channel:
				print(channel['Affiliate'])
			if 'ImageURL' in channel:
				print(channel['ImageURL'])
			if 'URL' in channel:
				print(channel['URL'])
			#VideoCodec
			#AudioCodec
			#HD
			#Favorite
			for program in channel["Guide"]:
				print("\t---------------PROGRAM---------------")
				print("\t" + program['Title'].encode('utf-8'))
				print("\t" + str(program['StartTime']))
				print("\t" + str(program['EndTime']))
				if 'EpisodeNumber' in program:
					print("\t" + program['EpisodeNumber'])
				if 'EpisodeTitle' in program:
					print("\t" + program['EpisodeTitle'])
				if 'Synopsis' in program:
					print("\t" + program['Synopsis'].encode('utf-8'))
				if 'OriginalAirdate' in program:
					print("\t" + str(program['OriginalAirdate']))
				print("\t" + program['SeriesID'])
				if 'PosterURL' in program:
					print("\t" + program['PosterURL'])
				if 'Filter' in program:
					for filter in program['Filter']:
						print("\t\t" + filter.encode('utf-8'))
	def process(self):		
		data = self.loadGuideFromWeb()
		
		xmltv = self.generatXMLTV(data)

		if self._outputpath is not None:
			if stat.S_ISSOCK(os.stat(self._outputpath).st_mode):
				client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
				try:
					client.connect(self._outputpath)
					client.sendall(xmltv.encode('utf8'))
				finally:
					client.close()
			else:
				with open(self._outputpath, 'w') as outfile:
					outfile.write(xmltv)
		else:
			print(xmltv)
							

  
if __name__== "__main__":
	parser = argparse.ArgumentParser(description='Generate XMLTV data from hdhomerun for a given hdhr device')
	parser.add_argument('--device-auth', default=None, help='Provide the device auth string instead of discovering it')
	parser.add_argument('--discover-url', default=None, help='Provide the discover url to get auth token (usually in the form http://<deviceip>/discover.json)')
	parser.add_argument('--tz-offset', default=None, help='Override the tz offset')
	parser.add_argument('--output', default=None, help='Output to this file (or socket), otherwise stdout')
	args = parser.parse_args()

	guide_fetcher = HDHRGuideData(args.output, args.discover_url, args.device_auth, args.tz_offset)
	guide_fetcher.process()
