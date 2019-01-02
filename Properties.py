import collections

class Properties(object):
	
	propfile = "/home/pi/Wecker/einstellungen.txt"

	def getProperties(self):
		# Datei in dictionary einlesen
		fobj = open(Properties.propfile, "r")
		content = {}
		for line in fobj: 
			if len(line) > 1:
				prop = line.split(" ")
				content[prop[0]] = prop[1].strip()

		fobj.close()

		# Eintraege sortieren
		return collections.OrderedDict(sorted(content.items()))


	def getProperty(self, id):
		# Einlesen
		content = self.getProperties()
		return content[id]


	def setProperty(self, id, val):
		# Einlesen
		content = self.getProperties()

		# loeschen und hinzufuegen des neuen Parameters
		fobj = open(Properties.propfile, "w")
		content[id] = val
		for i, v in content.iteritems():
			fobj.write(str(i) + " " + str(v) + "\n")
		fobj.close()
