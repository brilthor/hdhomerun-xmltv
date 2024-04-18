#!/usr/bin/env python

import os, re, json, datetime, subprocess
import xml.etree.ElementTree as ET
from urllib.request import urlopen
from xml.dom import minidom
from pprint import pprint

def loadGuideFromWeb():
	#device_ip = subprocess.check_output(["hdhomerun_config", "discover"]).split()[5]
	discover_url = json.loads(urlopen("http://ipv4-api.hdhomerun.com/discover").read().decode('utf-8'))[0]["DiscoverURL"]
	#print device_ip

	#device_auth = json.loads(urlopen("http://%s/discover.json" % device_ip).read().decode('utf-8'))['DeviceAuth']
	device_auth = json.loads(urlopen(discover_url).read().decode('utf-8'))['DeviceAuth']
	#print device_auth

	return json.loads(urlopen("https://ipv4-api.hdhomerun.com/api/guide.php?DeviceAuth=%s" % device_auth).read().decode('utf-8'))
	
def generatXMLTV(data):
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
			xmlProgram.set("start", datetime.datetime.fromtimestamp(program['StartTime']).strftime('%Y%m%d%H%M%S') + " " + timezone_offset)
			xmlProgram.set("stop", datetime.datetime.fromtimestamp(program['EndTime']).strftime('%Y%m%d%H%M%S') + " " + timezone_offset)
			ET.SubElement(xmlProgram, "title").text = program['Title']
			if 'EpisodeNumber' in program:
				ET.SubElement(xmlProgram, "episode-num").text = program['EpisodeNumber']
			if 'EpisodeTitle' in program:
				ET.SubElement(xmlProgram, "sub-title").text = program['EpisodeTitle']
			if 'Synopsis' in program:
				ET.SubElement(xmlProgram, "desc").text = program['Synopsis']
			if 'OriginalAirdate' in program:
				ET.SubElement(xmlProgram, "date").text = datetime.datetime.fromtimestamp(program['OriginalAirdate']).strftime('%Y%m%d%H%M%S') + " " + timezone_offset
			if 'PosterURL' in program:
				ET.SubElement(xmlProgram, "icon", src=program['PosterURL'])
			if 'Filter' in program:
				for filter in program['Filter']:
					ET.SubElement(xmlProgram, "category").text = filter
			

	#return ET.tostring(xml)

	reformed_xml = minidom.parseString(ET.tostring(xml).decode('utf-8'))
	return reformed_xml.toprettyxml(encoding='utf-8').decode('utf-8')

def printGuide(data):
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
					
def saveStringToFile(strData, filename):
	with open(filename, 'w') as outfile:
		outfile.write(strData)
					
def loadJsonFromFile(filename):
	return json.load(open(filename))

def saveJsonToFile(data, filename):
	with open(filename, 'w') as outfile:
		json.dump(data, outfile, indent=4)
					
def main():
	# from bard - change working directory to script
	abspath = os.path.abspath(__file__)
	dname = os.path.dirname(abspath)
	os.chdir(dname)
	 
	data = loadGuideFromWeb()
	#saveJsonToFile(data, "hdhomerun.json")
	#data = loadJsonFromFile("hdhomerun.json")
	
	xmltv = generatXMLTV(data)
	#print xmltv
	saveStringToFile(xmltv, "hdhomerun.xml")
	
	#printGuide(data)
  
if __name__== "__main__":
  main()
