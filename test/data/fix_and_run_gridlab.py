import os
import re

data_dir = os.path.dirname(__file__)

regex = r"object\svoltdump\s\{[\n\r\s]+filename\s[a-zA-Z]+\.csv;[\n\r\s]+mode\sRECT;[\n\r\s]+\}"

dumpstr = """


object voltdump {
     filename result.csv;
     mode RECT;
}
"""

for casefolder in os.walk(data_dir):
    casefile = os.path.join(casefolder[0], "node.glm")

    if not os.path.isfile(casefile):
        continue

    with open(casefile, 'r+') as file:
        filestr = file.read()

        if re.match(regex, filestr) == None:
            file.write(dumpstr)

