import os
import re
import subprocess

data_dir = os.path.dirname(__file__)

regex = r"object\svoltdump\s\{[\n\r\s]+filename\s[a-zA-Z]+\.csv;[\n\r\s]+mode\sRECT;[\n\r\s]+\}"

dumpstr = """


object voltdump {
     filename result.csv;
     mode RECT;
}
"""

for dirpath, dirnames, filenames in os.walk(data_dir):
    
    for filename in filenames:
        if not filename.endswith(".glm"):
            continue

        casefile = os.path.join(dirpath, filename)

        if not casefile.endswith("node.glm"):
            desiredcasefile = os.path.join(dirpath, "node.glm")
            os.rename(casefile, desiredcasefile)
            casefile = desiredcasefile

        with open(casefile, 'r+') as file:
            filestr = file.read()

            if re.search(regex, filestr) == None:
                file.write(dumpstr)
        
        print(f"Executing case {casefile}")
        subprocess.run(["gridlabd.exe", "node.glm"], cwd=dirpath)

